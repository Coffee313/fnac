#!/bin/bash

# FNAC Installation Script
# Downloads and configures FNAC + FreeRADIUS MAB

set -e

REPO_URL="https://github.com/Coffee313/fnac.git"
INSTALL_DIR="/opt/fnac"
SERVICE_NAME="fnac"
FNAC_USER="fnac"
FNAC_GROUP="fnac"

echo "=========================================="
echo "FNAC Installation Script"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "[1/7] Updating system packages..."
apt-get update

# Complete cleanup of broken FreeRADIUS
echo "Cleaning up any broken FreeRADIUS installation..."
systemctl stop freeradius 2>/dev/null || true
dpkg --remove --force-all freeradius freeradius-utils 2>/dev/null || true
apt-get clean
# Don't delete /etc/freeradius - we'll recreate it properly
rm -rf /var/lib/freeradius /var/cache/freeradius 2>/dev/null || true
apt-get --fix-broken install -y 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true

# Install dependencies
apt-get install -y python3 python3-pip python3-venv git

# Create freerad user BEFORE installing package
echo "Pre-creating FreeRADIUS user and directories..."
id -u freerad >/dev/null 2>&1 || useradd -r -s /bin/false freerad 2>/dev/null || true

# Create all required directories FIRST
mkdir -p /etc/freeradius/3.0/mods-enabled
mkdir -p /etc/freeradius/3.0/mods-available
mkdir -p /etc/freeradius/3.0/sites-enabled
mkdir -p /etc/freeradius/3.0/sites-available
mkdir -p /etc/freeradius/3.0/mods-config/attr_filter
mkdir -p /var/lib/freeradius
mkdir -p /var/run/freeradius
mkdir -p /var/log/freeradius/radacct

# Mask FreeRADIUS service to prevent it from starting during installation
echo "Masking FreeRADIUS service during installation..."
systemctl mask freeradius 2>/dev/null || true

# Install FreeRADIUS
echo "Installing FreeRADIUS..."
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends freeradius freeradius-utils 2>&1 || true

# Unmask FreeRADIUS service
echo "Unmasking FreeRADIUS service..."
systemctl unmask freeradius 2>/dev/null || true

# Stop FreeRADIUS if it started
systemctl stop freeradius 2>/dev/null || true
systemctl disable freeradius 2>/dev/null || true

# Create working radiusd.conf
echo "Creating FreeRADIUS configuration..."
cat > /etc/freeradius/3.0/radiusd.conf << 'RADIUSEOF'
prefix = /usr
exec_prefix = /usr
sysconfdir = /etc
localstatedir = /var
sbindir = /usr/sbin
logdir = /var/log/freeradius
radacctdir = /var/log/freeradius/radacct
confdir = /etc/freeradius/3.0
modconfdir = /etc/freeradius/3.0/mods-config
certdir = /etc/freeradius/3.0/certs
cadir = /etc/freeradius/3.0/certs
run_dir = /var/run/freeradius

umask = 0022

max_request_time = 30
cleanup_delay = 5
max_requests = 16384

listen {
    type = auth
    ipaddr = 0.0.0.0
    port = 1812
    proto = udp
}

listen {
    type = acct
    ipaddr = 0.0.0.0
    port = 1813
    proto = udp
}

modules {
    $INCLUDE mods-enabled/
}

$INCLUDE sites-enabled/
RADIUSEOF

# Create minimal working modules
echo "Creating FreeRADIUS modules..."

# Force create the directory and verify it exists
mkdir -p /etc/freeradius/3.0/mods-enabled
if [ ! -d "/etc/freeradius/3.0/mods-enabled" ]; then
    echo "ERROR: Cannot create /etc/freeradius/3.0/mods-enabled"
    ls -la /etc/freeradius/3.0/
    exit 1
fi

# PAP module
cat > /etc/freeradius/3.0/mods-enabled/pap << 'PAPEOF'
pap {
    auto_header = yes
}
PAPEOF

# Files module pointing to mab_users
cat > /etc/freeradius/3.0/mods-enabled/files << 'FILESEOF'
files {
    usersfile = ${confdir}/mab_users
}
FILESEOF

# Attr_filter module
cat > /etc/freeradius/3.0/mods-enabled/attr_filter << 'ATTREOF'
attr_filter attr_filter.access_reject {
    filename = ${modconfdir}/attr_filter/access-reject
}
ATTREOF

# Create access-reject file - MUST create directory first
mkdir -p /etc/freeradius/3.0/mods-config/attr_filter
cat > /etc/freeradius/3.0/mods-config/attr_filter/access-reject << 'REJECTEOF'
Reply-Message
REJECTEOF

# Detail module
cat > /etc/freeradius/3.0/mods-enabled/detail << 'DETAILEOF'
detail {
    filename = ${radacctdir}/detail
    header = "%t"
    permissions = 0600
    locking = no
    escape_user_name = no
}
DETAILEOF

# Create default site
echo "Creating default site configuration..."
mkdir -p /etc/freeradius/3.0/sites-available
cat > /etc/freeradius/3.0/sites-available/default << 'SITEEOF'
server default {
    authorize {
        files
    }
    authenticate {
        Auth-Type PAP {
            pap
        }
    }
    post-auth {
        Post-Auth-Type REJECT {
            attr_filter.access_reject
        }
    }
    accounting {
        detail
    }
}
SITEEOF

# Enable default site
mkdir -p /etc/freeradius/3.0/sites-enabled
ln -sf ../sites-available/default /etc/freeradius/3.0/sites-enabled/default 2>/dev/null || true

# Create empty mab_users file
touch /etc/freeradius/3.0/mab_users

# Set permissions
echo "Setting permissions..."
chown -R freerad:freerad /etc/freeradius/3.0 2>/dev/null || true
chown -R freerad:freerad /var/lib/freeradius 2>/dev/null || true
chown -R freerad:freerad /var/run/freeradius 2>/dev/null || true
chown -R freerad:freerad /var/log/freeradius 2>/dev/null || true

chmod 750 /etc/freeradius/3.0 2>/dev/null || true
[ -d /etc/freeradius/3.0/mods-enabled ] && chmod 750 /etc/freeradius/3.0/mods-enabled || true
[ -d /etc/freeradius/3.0/mods-available ] && chmod 750 /etc/freeradius/3.0/mods-available || true
[ -d /etc/freeradius/3.0/sites-enabled ] && chmod 750 /etc/freeradius/3.0/sites-enabled || true
[ -d /etc/freeradius/3.0/sites-available ] && chmod 750 /etc/freeradius/3.0/sites-available || true
[ -d /etc/freeradius/3.0/mods-config ] && chmod 750 /etc/freeradius/3.0/mods-config || true
[ -d /etc/freeradius/3.0/mods-config/attr_filter ] && chmod 750 /etc/freeradius/3.0/mods-config/attr_filter || true

chmod 640 /etc/freeradius/3.0/radiusd.conf 2>/dev/null || true
chmod 640 /etc/freeradius/3.0/mab_users 2>/dev/null || true
[ -f /etc/freeradius/3.0/mods-enabled/pap ] && chmod 640 /etc/freeradius/3.0/mods-enabled/pap || true
[ -f /etc/freeradius/3.0/mods-enabled/files ] && chmod 640 /etc/freeradius/3.0/mods-enabled/files || true
[ -f /etc/freeradius/3.0/mods-enabled/attr_filter ] && chmod 640 /etc/freeradius/3.0/mods-enabled/attr_filter || true
[ -f /etc/freeradius/3.0/mods-enabled/detail ] && chmod 640 /etc/freeradius/3.0/mods-enabled/detail || true
[ -f /etc/freeradius/3.0/sites-enabled/default ] && chmod 640 /etc/freeradius/3.0/sites-enabled/default || true
[ -f /etc/freeradius/3.0/mods-config/attr_filter/access-reject ] && chmod 640 /etc/freeradius/3.0/mods-config/attr_filter/access-reject || true

# Create systemd override
mkdir -p /etc/systemd/system/freeradius.service.d
cat > /etc/systemd/system/freeradius.service.d/override.conf << 'OVERRIDEEOF'
[Service]
Type=simple
ExecStartPre=
ExecStart=
ExecStart=/usr/sbin/freeradius -d /etc/freeradius/3.0 -f
StandardOutput=journal
StandardError=journal
OVERRIDEEOF
systemctl daemon-reload

echo "[2/7] Creating FNAC user and group..."
if ! id "$FNAC_USER" &>/dev/null; then
    groupadd -r "$FNAC_GROUP" 2>/dev/null || true
    useradd -r -g "$FNAC_GROUP" -d "$INSTALL_DIR" -s /bin/false "$FNAC_USER"
fi

# Add fnac to freerad group
usermod -a -G freerad fnac 2>/dev/null || true

# Allow fnac user to restart FreeRADIUS without password
echo "Configuring passwordless sudo for FNAC..."
mkdir -p /etc/sudoers.d
cat > /etc/sudoers.d/fnac-freeradius << 'SUDOEOF'
fnac ALL=(ALL) NOPASSWD: /bin/systemctl start freeradius
fnac ALL=(ALL) NOPASSWD: /bin/systemctl stop freeradius
fnac ALL=(ALL) NOPASSWD: /bin/systemctl restart freeradius
fnac ALL=(ALL) NOPASSWD: /bin/systemctl is-active freeradius
fnac ALL=(ALL) NOPASSWD: /usr/sbin/freeradius -C
SUDOEOF
chmod 440 /etc/sudoers.d/fnac-freeradius

echo "[3/7] Cloning FNAC repository..."
if [ -d "$INSTALL_DIR" ]; then
    echo "FNAC already installed at $INSTALL_DIR"
    read -p "Do you want to update it? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$INSTALL_DIR"
        git pull origin main
    fi
else
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

echo "[4/7] Setting up Python virtual environment..."
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "[5/7] Setting permissions..."
chown -R "$FNAC_USER:$FNAC_GROUP" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR/fnac.db" 2>/dev/null || true

# Fix sudo path issue in config generator - use full path to sudo
echo "Fixing sudo path in config generator..."
sed -i 's/\["sudo",/["\/usr\/bin\/sudo",/g' "$INSTALL_DIR/src/freeradius_config_generator.py"

echo "[6/7] Creating systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=FNAC - FreeRADIUS Management UI
After=network.target freeradius.service
Wants=freeradius.service

[Service]
Type=simple
User=$FNAC_USER
Group=$FNAC_GROUP
WorkingDirectory=$INSTALL_DIR
Environment="PATH=$INSTALL_DIR/venv/bin"
ExecStart=$INSTALL_DIR/venv/bin/python -m src.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable "$SERVICE_NAME"

echo "[7/7] Starting services..."

# Ensure FreeRADIUS is NOT masked
systemctl unmask freeradius 2>/dev/null || true
systemctl disable freeradius 2>/dev/null || true

# Make absolutely sure FreeRADIUS is stopped before starting
systemctl stop freeradius 2>/dev/null || true
sleep 2

# Start FNAC only
systemctl start "$SERVICE_NAME"

# Wait for FNAC to fully start and initialize database
echo "Waiting for FNAC to initialize..."
sleep 10

# Generate initial FreeRADIUS configuration from FNAC database
echo "Generating FreeRADIUS configuration from FNAC database..."
cd "$INSTALL_DIR"
source venv/bin/activate

# Create a Python script to generate the config
cat > /tmp/generate_config.py << 'GENEOF'
import sys
sys.path.insert(0, '/opt/fnac')

from src.device_manager import Device_Manager
from src.client_manager import Client_Manager
from src.policy_engine import Policy_Engine
from src.freeradius_config_generator import FreeRADIUSConfigGenerator

try:
    device_manager = Device_Manager()
    client_manager = Client_Manager()
    policy_engine = Policy_Engine()
    
    config_generator = FreeRADIUSConfigGenerator(
        device_manager=device_manager,
        client_manager=client_manager,
        policy_engine=policy_engine,
    )
    
    # Generate and write configuration
    success = config_generator.update_all_configs(reload=False, dry_run=False)
    
    if success:
        print("Configuration generated successfully")
        sys.exit(0)
    else:
        print("Failed to generate configuration")
        sys.exit(1)
        
except Exception as e:
    print(f"Error generating configuration: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
GENEOF

# Run the config generator as the fnac user
sudo -u fnac python3 /tmp/generate_config.py

if [ $? -eq 0 ]; then
    echo "Configuration generated successfully"
else
    echo "Warning: Failed to generate initial configuration"
    echo "This is normal if no devices/clients have been added yet"
fi

# Clean up temp script
rm -f /tmp/generate_config.py

# Now start FreeRADIUS
echo "Starting FreeRADIUS..."
systemctl start freeradius

# Wait for FreeRADIUS to start
sleep 3

# Verify FreeRADIUS is running
if systemctl is-active --quiet freeradius; then
    echo "FreeRADIUS started successfully"
else
    echo "Warning: FreeRADIUS failed to start"
    echo "Check logs with: sudo journalctl -u freeradius -n 50"
fi

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "FNAC is now running at: http://localhost:5000"
echo ""
echo "Useful commands:"
echo "  Start FNAC:      systemctl start fnac"
echo "  Stop FNAC:       systemctl stop fnac"
echo "  Status FNAC:     systemctl status fnac"
echo "  Logs FNAC:       journalctl -u fnac -f"
echo ""
echo "  Start FreeRADIUS:   sudo systemctl start freeradius"
echo "  Stop FreeRADIUS:    sudo systemctl stop freeradius"
echo "  Status FreeRADIUS:  sudo systemctl status freeradius"
echo "  Logs FreeRADIUS:    sudo journalctl -u freeradius -f"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:5000 in your browser"
echo "2. Create device groups and devices"
echo "3. Create client groups and clients with MAC addresses"
echo "4. Create policies for authentication"
echo "5. FreeRADIUS configuration will be updated automatically"
echo ""
