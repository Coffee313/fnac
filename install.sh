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
mkdir -p /var/lib/freeradius
mkdir -p /var/run/freeradius
chown -R freerad:freerad /etc/freeradius /var/lib/freeradius /var/run/freeradius 2>/dev/null || true
chmod -R 755 /etc/freeradius /var/lib/freeradius /var/run/freeradius 2>/dev/null || true

# Install FreeRADIUS - directories already exist so post-install won't fail
echo "Installing FreeRADIUS..."
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends freeradius freeradius-utils 2>&1 || true

# Stop FreeRADIUS if it started (it will fail due to incomplete config)
systemctl stop freeradius 2>/dev/null || true
systemctl disable freeradius 2>/dev/null || true

# Final verification and fix
mkdir -p /etc/freeradius/3.0/mods-config/files
mkdir -p /var/lib/freeradius
mkdir -p /var/run/freeradius
chown -R freerad:freerad /etc/freeradius /var/lib/freeradius /var/run/freeradius 2>/dev/null || true
chmod -R 755 /etc/freeradius /var/lib/freeradius /var/run/freeradius 2>/dev/null || true

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

echo "[7/7] Starting FNAC service..."
systemctl start "$SERVICE_NAME"

# Enable and start FreeRADIUS after FNAC is running
echo "Enabling FreeRADIUS service..."
systemctl enable freeradius
systemctl start freeradius

echo ""
echo "=========================================="
echo "Installation Complete!"
echo "=========================================="
echo ""
echo "FNAC is now running at: http://localhost:5000"
echo ""
echo "Useful commands:"
echo "  Start:   systemctl start $SERVICE_NAME"
echo "  Stop:    systemctl stop $SERVICE_NAME"
echo "  Status:  systemctl status $SERVICE_NAME"
echo "  Logs:    journalctl -u $SERVICE_NAME -f"
echo ""
echo "Next steps:"
echo "1. Open http://localhost:5000 in your browser"
echo "2. Create device groups and devices"
echo "3. Create client groups and clients"
echo "4. Create policies for authentication"
echo ""
