# RADIUS Server Deployment Guide for Astra Linux

This guide walks you through deploying and running the Simple RADIUS Server on your Astra Linux 1.7.5 virtual machine.

## Prerequisites

- Astra Linux 1.7.5 (or compatible Debian-based system)
- Python 3.8 or higher
- sudo/root access for port binding (UDP 1812 requires elevated privileges)
- Git (optional, for cloning the repository)

## Step 1: Prepare Your System

### Update system packages
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Python and pip
```bash
sudo apt install -y python3 python3-pip python3-venv
```

### Verify Python version
```bash
python3 --version
```

## Step 2: Set Up the Project

### Clone or copy the project to your VM
If you have the project on your host machine, copy it to the VM:
```bash
# From your host machine
scp -r /path/to/simple-radius-server user@astra-vm:/home/user/
```

Or if already on the VM, navigate to the project directory:
```bash
cd /path/to/simple-radius-server
```

### Create a Python virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### Install dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## Step 3: Configure the Server

### Create configuration directory
```bash
sudo mkdir -p /etc/radius-server
sudo chown $USER:$USER /etc/radius-server
```

### Initialize data files (optional - they'll be created automatically)
```bash
# The server will create these automatically on first run
# But you can pre-create them if needed:
touch /etc/radius-server/devices.json
touch /etc/radius-server/clients.json
touch /etc/radius-server/policies.json
touch /etc/radius-server/logs.json
```

## Step 4: Run the Server

### Option A: Run with elevated privileges (required for UDP 1812)

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Run the server with sudo
sudo -E python3 -m src.main
```

The `-E` flag preserves your environment variables and virtual environment.

### Option B: Run on a different port (for testing without sudo)

If you want to test without elevated privileges, modify the port in `src/radius_server.py`:

```python
# Change from 1812 to a higher port (e.g., 11812)
UDP_PORT = 11812
```

Then run normally:
```bash
python3 -m src.main
```

## Step 5: Access the Configuration Interface

Once the server is running, the Flask API will be available at:

```
http://localhost:5000
```

### Web UI
- Device Management: `http://localhost:5000/devices`
- Client Management: `http://localhost:5000/clients`
- Policy Management: `http://localhost:5000/policies`
- Log Viewer: `http://localhost:5000/logs`

### REST API Endpoints

**Devices:**
- `GET /api/devices` - List all devices
- `POST /api/devices` - Create device
- `PUT /api/devices/{id}` - Update device
- `DELETE /api/devices/{id}` - Delete device

**Device Groups:**
- `GET /api/device-groups` - List all device groups
- `POST /api/device-groups` - Create group
- `DELETE /api/device-groups/{id}` - Delete group

**Clients:**
- `GET /api/clients` - List all clients
- `POST /api/clients` - Create client
- `PUT /api/clients/{mac}` - Update client
- `DELETE /api/clients/{mac}` - Delete client

**Client Groups:**
- `GET /api/client-groups` - List all client groups
- `POST /api/client-groups` - Create group
- `DELETE /api/client-groups/{id}` - Delete group

**Policies:**
- `GET /api/policies` - List all policies
- `POST /api/policies` - Create policy
- `PUT /api/policies/{id}` - Update policy
- `DELETE /api/policies/{id}` - Delete policy

**Logs:**
- `GET /api/logs` - List logs (supports filters: date_start, date_end, mac_address, outcome)

## Step 6: Test the Server

### Run unit tests
```bash
pytest tests/ -v
```

### Run property-based tests
```bash
pytest tests/ -v --hypothesis-seed=0
```

### Run specific test file
```bash
pytest tests/test_device_manager.py -v
```

## Step 7: Configure Initial Data

### Example: Add a device via API

```bash
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "access-layer", "name": "Access Layer Switches"}'

curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key-12345",
    "device_group_id": "access-layer"
  }'
```

### Example: Add a client via API

```bash
curl -X POST http://localhost:5000/api/client-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "printers", "name": "Network Printers"}'

curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:11:22:33:44:55",
    "client_group_id": "printers"
  }'
```

### Example: Create a policy via API

```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "printers",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 100
  }'
```

## Step 8: Monitor Logs

### View authentication logs
```bash
curl http://localhost:5000/api/logs | python3 -m json.tool
```

### Filter logs by MAC address
```bash
curl "http://localhost:5000/api/logs?mac_address=00:11:22:33:44:55" | python3 -m json.tool
```

### Filter logs by outcome
```bash
curl "http://localhost:5000/api/logs?outcome=SUCCESS" | python3 -m json.tool
```

## Step 9: Run as a Service (Optional)

### Create a systemd service file

```bash
sudo nano /etc/systemd/system/radius-server.service
```

Add the following content:

```ini
[Unit]
Description=Simple RADIUS Server
After=network.target

[Service]
Type=simple
User=radius
WorkingDirectory=/home/radius/simple-radius-server
Environment="PATH=/home/radius/simple-radius-server/venv/bin"
ExecStart=/home/radius/simple-radius-server/venv/bin/python3 -m src.main
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Create radius user
```bash
sudo useradd -r -s /bin/false radius
sudo chown -R radius:radius /etc/radius-server
```

### Enable and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable radius-server
sudo systemctl start radius-server
```

### Check service status
```bash
sudo systemctl status radius-server
```

### View service logs
```bash
sudo journalctl -u radius-server -f
```

## Troubleshooting

### Port 1812 already in use
```bash
# Find what's using port 1812
sudo lsof -i :1812

# Kill the process if needed
sudo kill -9 <PID>
```

### Permission denied on port 1812
RADIUS requires UDP port 1812, which is a privileged port. You must run with `sudo` or use a higher port for testing.

### Import errors
Make sure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Data files not found
The server creates data files automatically in `/etc/radius-server/`. Ensure the directory exists and is writable:
```bash
ls -la /etc/radius-server/
```

## Next Steps

1. Configure your network devices to send RADIUS requests to this server
2. Add devices and clients through the web UI or API
3. Create policies to control network access
4. Monitor authentication logs in real-time
5. Set up the systemd service for production deployment

## Support

For issues or questions, check:
- Application logs: `/var/log/radius-server.log` (if configured)
- Test suite: `pytest tests/ -v`
- API documentation: Check individual endpoint implementations in `src/api.py`
