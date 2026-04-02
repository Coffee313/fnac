# FNAC Installation Guide

## Quick Install (Recommended)

### Prerequisites
- Linux system (Ubuntu 20.04+ or Debian 11+)
- Root or sudo access
- Internet connection

### Installation

**One-line installation:**
```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/Coffee313/fnac/main/install.sh)"
```

**Or manual installation:**
```bash
# Clone the repository
git clone https://github.com/Coffee313/fnac.git
cd fnac

# Run the installation script
sudo bash install.sh
```

### What the installer does:
1. Updates system packages
2. Installs Python 3, pip, git, and FreeRADIUS
3. Creates a dedicated `fnac` user
4. Clones the FNAC repository to `/opt/fnac`
5. Sets up Python virtual environment
6. Installs Python dependencies
7. Creates a systemd service for automatic startup
8. Starts the FNAC service

### Access FNAC

After installation, open your browser and navigate to:
```
http://localhost:5000
```

## Repository

FNAC is hosted at: https://github.com/Coffee313/fnac

The repository is public, so no authentication is required for installation.

## Service Management

### Start FNAC
```bash
sudo systemctl start fnac
```

### Stop FNAC
```bash
sudo systemctl stop fnac
```

### Check Status
```bash
sudo systemctl status fnac
```

### View Logs
```bash
sudo journalctl -u fnac -f
```

### Enable/Disable Auto-start
```bash
# Enable (default)
sudo systemctl enable fnac

# Disable
sudo systemctl disable fnac
```

## Uninstallation

To completely remove FNAC:

```bash
sudo bash uninstall.sh
```

Or manually:

```bash
# Stop the service
sudo systemctl stop fnac
sudo systemctl disable fnac

# Remove the installation
sudo rm -rf /opt/fnac

# Remove the systemd service
sudo rm /etc/systemd/system/fnac.service
sudo systemctl daemon-reload

# Remove the user (optional)
sudo userdel fnac
sudo groupdel fnac
```

## Configuration

### Change Port

Edit `/opt/fnac/src/main.py` and modify the Flask port:

```python
app.run(host='0.0.0.0', port=8080, debug=False)
```

Then restart:
```bash
sudo systemctl restart fnac
```

### Change Installation Directory

Modify the `INSTALL_DIR` variable in `install.sh` before running it.

## Troubleshooting

### FNAC won't start
```bash
# Check logs
sudo journalctl -u fnac -n 50

# Check if port 5000 is in use
sudo netstat -tlnp | grep 5000
```

### FreeRADIUS not responding
```bash
# Check FreeRADIUS status
sudo systemctl status freeradius

# Check FreeRADIUS logs
sudo tail -f /var/log/freeradius/radius.log
```

### Permission denied errors
```bash
# Fix permissions
sudo chown -R fnac:fnac /opt/fnac
sudo chmod 755 /opt/fnac
```

## Next Steps

1. Open http://localhost:5000
2. Create device groups (e.g., "switches", "access-points")
3. Add network devices with their IP addresses and shared secrets
4. Create client groups (e.g., "trusted", "guest")
5. Add MAC addresses of devices to authenticate
6. Create policies to assign VLANs or reject access

## Security Notes

- Currently uses HTTP. For production, configure HTTPS with a reverse proxy (nginx/Apache)
- Change FreeRADIUS shared secrets from defaults
- Restrict access to port 5000 using firewall rules
- Run FNAC behind a reverse proxy with authentication

## Support

For issues or questions, visit: https://github.com/yourusername/fnac/issues
