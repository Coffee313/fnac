# FNAC - RADIUS Server

A lightweight, Python-based RADIUS server implementing MAC Authentication Bypass (MAB) for network access control. Designed for Debian-based systems (tested on Astra Linux 1.7.5).

## Features

- **RFC 2865 Compliant**: Full RADIUS protocol implementation
- **MAC Authentication Bypass (MAB)**: Authenticate network devices by MAC address
- **Policy-Based Access Control**: Define authentication policies per client group
- **VLAN Assignment**: Automatically assign VLANs to authenticated clients
- **Audit Logging**: Complete authentication event logging with visual indicators
- **Web Configuration Interface**: User-friendly web UI and REST API
- **Data Persistence**: All configuration and logs survive server restarts
- **Property-Based Testing**: Comprehensive correctness validation

## Quick Start

### 1. Setup (one-time)
```bash
./quickstart.sh setup
```

### 2. Run the server
```bash
./quickstart.sh run
```

### 3. Access the web UI
Open http://localhost:5000 in your browser

### 4. Configure via API
```bash
# Create a device group
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "switches", "name": "Network Switches"}'

# Add a device
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key",
    "device_group_id": "switches"
  }'
```

See [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md) for a complete walkthrough.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RADIUS_Server                             │
│  (UDP 1812 listener, RFC 2865 protocol handler)             │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┬──────────────┐
    │            │            │              │              │
    ▼            ▼            ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Device_ │ │ Client_ │ │ Policy_  │ │   Log_   │ │Persistence
│Manager  │ │Manager  │ │ Engine   │ │ Manager  │ │ Layer
└─────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘
```

## Components

### Device_Manager
Manages network devices (switches, access points) that send RADIUS requests.
- Create/update/delete devices
- Organize devices into groups
- Verify device identity by IP and shared secret

### Client_Manager
Manages client MAC addresses and their group assignments.
- Add/remove clients by MAC address
- Organize clients into groups
- Validate MAC address format

### Policy_Engine
Defines authentication policies for client groups.
- Accept with VLAN assignment
- Accept without VLAN
- Reject access

### Log_Manager
Records and displays authentication events.
- Log all authentication attempts
- Filter by date, MAC address, or outcome
- Visual indicators (green/red) for success/failure

### RADIUS_Server
Handles RADIUS protocol and orchestrates authentication.
- Listen on UDP 1812
- Verify device credentials
- Extract client MAC from request
- Evaluate policies
- Generate RADIUS responses

## API Endpoints

### Devices
- `GET /api/devices` - List all devices
- `POST /api/devices` - Create device
- `PUT /api/devices/{id}` - Update device
- `DELETE /api/devices/{id}` - Delete device

### Device Groups
- `GET /api/device-groups` - List groups
- `POST /api/device-groups` - Create group
- `DELETE /api/device-groups/{id}` - Delete group

### Clients
- `GET /api/clients` - List all clients
- `POST /api/clients` - Create client
- `PUT /api/clients/{mac}` - Update client
- `DELETE /api/clients/{mac}` - Delete client

### Client Groups
- `GET /api/client-groups` - List groups
- `POST /api/client-groups` - Create group
- `DELETE /api/client-groups/{id}` - Delete group

### Policies
- `GET /api/policies` - List all policies
- `POST /api/policies` - Create policy
- `PUT /api/policies/{id}` - Update policy
- `DELETE /api/policies/{id}` - Delete policy

### Logs
- `GET /api/logs` - List logs (supports filters)
  - Query params: `date_start`, `date_end`, `mac_address`, `outcome`

## Installation

### Prerequisites
- Python 3.8+
- Debian-based Linux (Astra Linux 1.7.5 recommended)
- sudo access (for UDP 1812 binding)

### Install Dependencies
```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# Clone or copy the project
cd simple-radius-server

# Setup
./quickstart.sh setup
```

## Usage

### Start the server
```bash
./quickstart.sh run
```

### Run tests
```bash
./quickstart.sh test
```

### Clean up
```bash
./quickstart.sh clean
```

## Configuration

### Data Storage
Configuration and logs are stored in JSON files:
- `/etc/radius-server/devices.json`
- `/etc/radius-server/clients.json`
- `/etc/radius-server/policies.json`
- `/etc/radius-server/logs.json`

### Ports
- **RADIUS**: UDP 1812 (requires elevated privileges)
- **Web UI/API**: HTTP 5000

### Shared Secrets
Each device has a shared secret used for RADIUS message authentication. Use strong, unique secrets (16+ characters recommended).

## Testing

### Run all tests
```bash
./quickstart.sh test
```

### Run specific test file
```bash
source venv/bin/activate
pytest tests/test_device_manager.py -v
```

### Run with coverage
```bash
source venv/bin/activate
pytest tests/ --cov=src --cov-report=html
```

## Production Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for:
- Systemd service setup
- Running as a background service
- Log rotation
- Monitoring and troubleshooting

## Example Workflow

1. **Add a network device**
   ```bash
   curl -X POST http://localhost:5000/api/devices \
     -H "Content-Type: application/json" \
     -d '{
       "id": "switch-01",
       "ip_address": "192.168.1.100",
       "shared_secret": "secret123",
       "device_group_id": "access-layer"
     }'
   ```

2. **Add a client**
   ```bash
   curl -X POST http://localhost:5000/api/clients \
     -H "Content-Type: application/json" \
     -d '{
       "mac_address": "00:11:22:33:44:55",
       "client_group_id": "printers"
     }'
   ```

3. **Create a policy**
   ```bash
   curl -X POST http://localhost:5000/api/policies \
     -H "Content-Type: application/json" \
     -d '{
       "client_group_id": "printers",
       "decision": "ACCEPT_WITH_VLAN",
       "vlan_id": 100
     }'
   ```

4. **Monitor authentication**
   ```bash
   curl http://localhost:5000/api/logs | python3 -m json.tool
   ```

## Troubleshooting

### Port 1812 already in use
```bash
sudo lsof -i :1812
sudo kill -9 <PID>
```

### Permission denied
RADIUS requires elevated privileges for UDP 1812. Run with `sudo`:
```bash
sudo -E ./quickstart.sh run
```

### Import errors
Ensure you're in the virtual environment:
```bash
source venv/bin/activate
```

### Data files not found
The server creates data files automatically. Ensure `/etc/radius-server/` exists:
```bash
sudo mkdir -p /etc/radius-server
sudo chown $USER:$USER /etc/radius-server
```

## Project Structure

```
simple-radius-server/
├── src/
│   ├── main.py                 # Entry point
│   ├── api.py                  # Flask REST API
│   ├── models.py               # Data models
│   ├── persistence.py          # JSON persistence layer
│   ├── device_manager.py       # Device management
│   ├── client_manager.py       # Client management
│   ├── policy_engine.py        # Policy evaluation
│   ├── log_manager.py          # Authentication logging
│   ├── radius_server.py        # RADIUS protocol handler
│   ├── radius_protocol.py      # RFC 2865 implementation
│   └── logging_config.py       # Logging setup
├── tests/
│   ├── test_device_manager.py
│   ├── test_client_manager.py
│   ├── test_policy_engine.py
│   ├── test_log_manager.py
│   ├── test_persistence.py
│   ├── test_radius_server.py
│   └── test_api.py
├── requirements.txt            # Python dependencies
├── quickstart.sh              # Quick-start script
├── DEPLOYMENT_GUIDE.md        # Production deployment
├── EXAMPLE_SETUP.md           # Configuration examples
└── README.md                  # This file
```

## Requirements

See [requirements.txt](requirements.txt) for Python dependencies:
- pyrad: RADIUS protocol library
- flask: Web framework
- pytest: Testing framework
- hypothesis: Property-based testing
- python-dateutil: Date utilities

## License

This project is provided as-is for network access control purposes.

## Support

For issues or questions:
1. Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for troubleshooting
2. Review [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md) for configuration examples
3. Run tests to verify installation: `./quickstart.sh test`
4. Check application logs for error details

## Next Steps

1. Follow [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md) to configure your first server
2. Test with RADIUS client tools: `radtest`
3. Configure your network devices to send RADIUS requests
4. Monitor authentication logs in real-time
5. Deploy as a systemd service for production use
