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
rm -rf /etc/freeradius /var/lib/freeradius /var/cache/freeradius 2>/dev/null || true
apt-get --fix-broken install -y 2>/dev/null || true
apt-get autoremove -y 2>/dev/null || true

# Install dependencies
apt-get install -y python3 python3-pip python3-venv git

# Create freerad user and directories BEFORE installing package
echo "Pre-creating FreeRADIUS user and directories..."
id -u freerad >/dev/null 2>&1 || useradd -r -s /bin/false freerad 2>/dev/null || true
mkdir -p /etc/freeradius/3.0/mods-config/files
mkdir -p /etc/freeradius/3.0/mods-enabled
mkdir -p /etc/freeradius/3.0/sites-enabled
mkdir -p /var/lib/freeradius
mkdir -p /var/run/freeradius
mkdir -p /var/log/freeradius/radacct
chown -R freerad:freerad /etc/freeradius /var/lib/freeradius /var/run/freeradius /var/log/freeradius 2>/dev/null || true
chmod -R 755 /etc/freeradius /var/lib/freeradius /var/run/freeradius /var/log/freeradius 2>/dev/null || true

# Create minimal radiusd.conf BEFORE installing package
echo "Creating minimal FreeRADIUS configuration..."
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

# Set umask so log files are readable by all users
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
    always ok {
        rcode = ok
    }
}

$INCLUDE mods-enabled/
$INCLUDE sites-enabled/
RADIUSEOF
chown freerad:freerad /etc/freeradius/3.0/radiusd.conf
chmod 640 /etc/freeradius/3.0/radiusd.conf

# Create log file that FreeRADIUS expects
touch /var/log/freeradius/radius.log
chown freerad:freerad /var/log/freeradius/radius.log
# Make log file readable by all users so FNAC can parse it
chmod 644 /var/log/freeradius/radius.log

# Also create the /usr/var/log directory that package config expects (as fallback)
mkdir -p /usr/var/log
touch /usr/var/log/radius.log
chmod 666 /usr/var/log/radius.log

# Make log directory readable by all users so FNAC can access log files
chmod 755 /var/log/freeradius
chmod 755 /var/log/freeradius/radacct

# Mask FreeRADIUS service to prevent it from starting during installation
echo "Masking FreeRADIUS service during installation..."
systemctl mask freeradius 2>/dev/null || true

# Install FreeRADIUS - directories and config already exist so post-install won't fail
echo "Installing FreeRADIUS..."
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends freeradius freeradius-utils 2>&1 || true

# Unmask FreeRADIUS service
echo "Unmasking FreeRADIUS service..."
systemctl unmask freeradius 2>/dev/null || true

# Stop FreeRADIUS if it started
systemctl stop freeradius 2>/dev/null || true
systemctl disable freeradius 2>/dev/null || true

# Create systemd override to force FreeRADIUS to use our config
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

# Ensure FreeRADIUS is NOT masked (so FNAC can start it later)
systemctl unmask freeradius 2>/dev/null || true
systemctl disable freeradius 2>/dev/null || true
systemctl stop freeradius 2>/dev/null || true

# Create FNAC-owned FreeRADIUS config directory
mkdir -p /opt/fnac/freeradius_config
chown -R fnac:fnac /opt/fnac/freeradius_config
chmod -R 755 /opt/fnac/freeradius_config

# Create symlink from /etc/freeradius/3.0 to FNAC's config directory
rm -rf /etc/freeradius/3.0
ln -s /opt/fnac/freeradius_config /etc/freeradius/3.0

# Initialize FNAC's FreeRADIUS config directory
mkdir -p /opt/fnac/freeradius_config/mods-enabled
mkdir -p /opt/fnac/freeradius_config/sites-enabled
mkdir -p /opt/fnac/freeradius_config/mods-config/files

# Create initial config files in FNAC directory
cat > /opt/fnac/freeradius_config/radiusd.conf << 'RADIUSEOF'
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

# Set umask so log files are readable by all users
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
    always ok {
        rcode = ok
    }
}

$INCLUDE mods-enabled/
$INCLUDE sites-enabled/
RADIUSEOF

cat > /opt/fnac/freeradius_config/sites-enabled/default << 'SITEEOF'
server default {
    authorize {
        ok
    }
    authenticate {
        ok
    }
    accounting {
        ok
    }
    session {
        ok
    }
    post-auth {
        ok
    }
}
SITEEOF

cat > /opt/fnac/freeradius_config/mods-enabled/files << 'FILESEOF'
files {
	usersfile = ${confdir}/mab_users
}
FILESEOF

touch /opt/fnac/freeradius_config/clients.conf
touch /opt/fnac/freeradius_config/mab_users

# Set permissions so FNAC can write to everything
chown -R fnac:fnac /opt/fnac/freeradius_config

# Make directories world-writable so FNAC can create/modify files
chmod 777 /opt/fnac/freeradius_config
chmod 777 /opt/fnac/freeradius_config/mods-enabled
chmod 777 /opt/fnac/freeradius_config/sites-enabled
chmod 777 /opt/fnac/freeradius_config/mods-config

# Make config files world-readable and writable so both FNAC and FreeRADIUS can access them
chmod 666 /opt/fnac/freeradius_config/clients.conf
chmod 666 /opt/fnac/freeradius_config/mab_users
chmod 666 /opt/fnac/freeradius_config/radiusd.conf
chmod 666 /opt/fnac/freeradius_config/mods-enabled/files
chmod 666 /opt/fnac/freeradius_config/sites-enabled/default

# Start FNAC only
systemctl start "$SERVICE_NAME"

# Wait for FNAC to start
sleep 5

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
echo "3. Create client groups and clients"
echo "4. Create policies for authentication"
echo "5. FreeRADIUS will start automatically when you create your first device"
echo ""
