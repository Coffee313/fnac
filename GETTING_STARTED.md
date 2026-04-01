# Getting Started with RADIUS Server on Astra Linux

This is your step-by-step guide to get the RADIUS server running on your Astra Linux VM in under 10 minutes.

## What You'll Have

A fully functional RADIUS server that:
- Authenticates network devices by MAC address
- Assigns VLANs based on policies
- Logs all authentication events
- Provides a web interface for configuration
- Persists all data across restarts

## Prerequisites

- Astra Linux 1.7.5 (or any Debian-based system)
- Python 3.8 or higher
- Internet connection (for downloading dependencies)
- Terminal access

## Step 1: Prepare Your System (2 minutes)

Open a terminal and run:

```bash
# Update system packages
sudo apt update
sudo apt upgrade -y

# Install Python and required tools
sudo apt install -y python3 python3-pip python3-venv curl
```

Verify Python is installed:
```bash
python3 --version
```

## Step 2: Get the Code (1 minute)

If you have the code on your host machine, copy it to the VM:

```bash
# From your host machine (Windows/Mac/Linux)
scp -r /path/to/simple-radius-server user@astra-vm:/home/user/
```

Or if already on the VM, navigate to the project directory:

```bash
cd /path/to/simple-radius-server
```

## Step 3: Initial Setup (3 minutes)

Run the setup script:

```bash
./quickstart.sh setup
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Create the configuration directory
- Prepare the system

## Step 4: Start the Server (1 minute)

```bash
./quickstart.sh run
```

You should see output like:
```
[*] Starting RADIUS Server...
[*] RADIUS Server starting on UDP 1812 and HTTP 5000
[!] Note: UDP 1812 requires elevated privileges. Running with sudo...
```

The server is now running! Leave this terminal open.

## Step 5: Configure Your First Device (2 minutes)

Open a **new terminal** and run these commands:

### Create a device group
```bash
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "switches", "name": "Network Switches"}'
```

### Add a network device
```bash
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key-12345",
    "device_group_id": "switches"
  }'
```

### Create a client group
```bash
curl -X POST http://localhost:5000/api/client-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "printers", "name": "Network Printers"}'
```

### Add a client (MAC address)
```bash
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:11:22:33:44:55",
    "client_group_id": "printers"
  }'
```

### Create a policy
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "printers",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 100
  }'
```

## Step 6: Access the Web Interface

Open your browser and go to:

```
http://localhost:5000
```

You should see the RADIUS server dashboard with tabs for:
- **Devices**: View and manage network devices
- **Clients**: View and manage MAC addresses
- **Policies**: View and manage authentication policies
- **Logs**: View authentication events in real-time

## Step 7: Test Authentication

In your second terminal, test if everything works:

```bash
# View all logs
curl http://localhost:5000/api/logs | python3 -m json.tool

# Filter logs by MAC address
curl "http://localhost:5000/api/logs?mac_address=00:11:22:33:44:55" | python3 -m json.tool
```

## What's Next?

### Option A: Continue Testing
See [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md) for more configuration examples and testing scenarios.

### Option B: Deploy to Production
See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) to:
- Run as a systemd service
- Set up automatic startup
- Configure logging
- Monitor the server

### Option C: Quick Reference
See [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common commands and troubleshooting.

## Common Tasks

### Stop the Server
Press `Ctrl+C` in the terminal where the server is running.

### Restart the Server
```bash
# In the server terminal, press Ctrl+C
# Then run again
./quickstart.sh run
```

### Run Tests
```bash
# In a new terminal
./quickstart.sh test
```

### View Configuration Files
```bash
# All configuration is stored here
ls -la /etc/radius-server/

# View devices
cat /etc/radius-server/devices.json | python3 -m json.tool
```

## Troubleshooting

### "Permission denied" error
The RADIUS server needs elevated privileges to use port 1812. The script handles this automatically with `sudo`.

### "Address already in use"
Another process is using port 1812 or 5000:
```bash
# Find what's using the ports
sudo lsof -i :1812
sudo lsof -i :5000

# Kill the process if needed
sudo kill -9 <PID>
```

### "ModuleNotFoundError"
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Can't access web UI
Check if the server is running:
```bash
ps aux | grep python3 | grep src.main
```

If not running, start it:
```bash
./quickstart.sh run
```

## Key Concepts

### Devices
Network equipment (switches, access points) that send RADIUS authentication requests. Each device has:
- **ID**: Unique identifier
- **IP Address**: Where the device is located
- **Shared Secret**: Password for RADIUS communication

### Clients
End devices identified by MAC address that want to connect to the network.

### Policies
Rules that determine what happens when a client tries to authenticate:
- **Accept with VLAN**: Allow connection and assign to a VLAN
- **Accept without VLAN**: Allow connection without VLAN assignment
- **Reject**: Deny connection

### Logs
Records of all authentication attempts showing:
- When it happened
- Which client (MAC address)
- Which device
- Whether it succeeded or failed
- Which VLAN was assigned (if applicable)

## File Structure

```
simple-radius-server/
├── src/                    # Python source code
├── tests/                  # Test suite
├── requirements.txt        # Python dependencies
├── quickstart.sh          # Quick-start script
├── README.md              # Full documentation
├── GETTING_STARTED.md     # This file
├── EXAMPLE_SETUP.md       # Configuration examples
├── DEPLOYMENT_GUIDE.md    # Production deployment
└── QUICK_REFERENCE.md     # Common commands
```

## Data Persistence

All your configuration is automatically saved to:
```
/etc/radius-server/
├── devices.json           # Device configuration
├── clients.json           # Client MAC addresses
├── policies.json          # Authentication policies
└── logs.json              # Authentication logs
```

These files persist across server restarts, so your configuration is safe.

## Next Steps

1. ✅ You've set up the server
2. ✅ You've configured your first device and client
3. ✅ You've created a policy
4. 📖 Read [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md) for more examples
5. 🚀 Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for production setup
6. 📚 Read [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for common commands

## Support

If you get stuck:

1. **Check the logs**: `curl http://localhost:5000/api/logs`
2. **Run tests**: `./quickstart.sh test`
3. **Read the guides**: See the documentation files above
4. **Check troubleshooting**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#troubleshooting)

## Success!

You now have a working RADIUS server on Astra Linux. You can:
- ✅ Authenticate network devices
- ✅ Manage MAC addresses
- ✅ Assign VLANs
- ✅ View authentication logs
- ✅ Configure everything via web UI or API

Congratulations! 🎉
