#!/bin/bash

# FNAC Uninstallation Script
# Removes FNAC and cleans up

set -e

INSTALL_DIR="/opt/fnac"
SERVICE_NAME="fnac"
FNAC_USER="fnac"
FNAC_GROUP="fnac"

echo "=========================================="
echo "FNAC Uninstallation Script"
echo "=========================================="

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root"
   exit 1
fi

echo "WARNING: This will remove FNAC and all its data!"
read -p "Are you sure you want to uninstall FNAC? (yes/no) " -r
echo
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo "Uninstallation cancelled"
    exit 0
fi

echo "[1/5] Stopping FNAC service..."
systemctl stop "$SERVICE_NAME" 2>/dev/null || true
systemctl disable "$SERVICE_NAME" 2>/dev/null || true

echo "[2/5] Removing systemd service..."
rm -f "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload

echo "[3/5] Removing FNAC installation..."
rm -rf "$INSTALL_DIR"

echo "[4/5] Removing FNAC user and group..."
userdel "$FNAC_USER" 2>/dev/null || true
groupdel "$FNAC_GROUP" 2>/dev/null || true

echo "[5/5] Cleaning up..."
# Remove FreeRADIUS configuration and data
echo "Removing FreeRADIUS configuration..."
rm -rf /etc/freeradius/3.0/mods-config/files/authorize.fnac 2>/dev/null || true
rm -rf /etc/freeradius/3.0/sites-available/fnac 2>/dev/null || true
rm -rf /etc/freeradius/3.0/sites-enabled/fnac 2>/dev/null || true
rm -rf /etc/freeradius/3.0/mods-enabled/fnac* 2>/dev/null || true
rm -rf /etc/freeradius/3.0/mods-available/fnac* 2>/dev/null || true

# Restart FreeRADIUS to reload configuration
systemctl restart freeradius 2>/dev/null || true

echo ""
echo "=========================================="
echo "Uninstallation Complete!"
echo "=========================================="
echo ""
echo "FNAC has been removed from $INSTALL_DIR"
echo ""
echo "FreeRADIUS configuration has been cleaned."
echo "To completely remove FreeRADIUS:"
echo "  sudo apt-get remove freeradius freeradius-utils"
echo ""
