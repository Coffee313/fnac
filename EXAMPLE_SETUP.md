# Example Setup: Configuring Your First RADIUS Server

This guide shows you how to set up a working RADIUS server with example devices, clients, and policies.

## Quick Setup (5 minutes)

### 1. Start the server
```bash
./quickstart.sh setup
./quickstart.sh run
```

The server will start on:
- **RADIUS**: UDP 1812 (for network devices)
- **Web UI**: http://localhost:5000
- **API**: http://localhost:5000/api

### 2. Create device groups and devices

Open a new terminal and run:

```bash
# Create a device group for access layer switches
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{
    "id": "access-layer",
    "name": "Access Layer Switches"
  }'

# Create a device (network switch)
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key-12345",
    "device_group_id": "access-layer"
  }'
```

### 3. Create client groups and clients

```bash
# Create a client group for printers
curl -X POST http://localhost:5000/api/client-groups \
  -H "Content-Type: application/json" \
  -d '{
    "id": "printers",
    "name": "Network Printers"
  }'

# Add a printer client
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:11:22:33:44:55",
    "client_group_id": "printers"
  }'

# Create a client group for workstations
curl -X POST http://localhost:5000/api/client-groups \
  -H "Content-Type: application/json" \
  -d '{
    "id": "workstations",
    "name": "User Workstations"
  }'

# Add a workstation client
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "client_group_id": "workstations"
  }'
```

### 4. Create policies

```bash
# Policy for printers: Accept with VLAN 100
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "printers",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 100
  }'

# Policy for workstations: Accept with VLAN 200
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "workstations",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 200
  }'
```

### 5. View logs

```bash
# List all authentication logs
curl http://localhost:5000/api/logs | python3 -m json.tool

# Filter by MAC address
curl "http://localhost:5000/api/logs?mac_address=00:11:22:33:44:55" | python3 -m json.tool

# Filter by outcome (SUCCESS or FAILURE)
curl "http://localhost:5000/api/logs?outcome=SUCCESS" | python3 -m json.tool
```

## Testing with a RADIUS Client

### Install radtest (RADIUS client tool)

```bash
sudo apt install -y freeradius-utils
```

### Send a test authentication request

```bash
# Test authentication for printer (should succeed with VLAN 100)
radtest -t pap 00:11:22:33:44:55 00:11:22:33:44:55 localhost 1812 my-secret-key-12345

# Test authentication for workstation (should succeed with VLAN 200)
radtest -t pap AA:BB:CC:DD:EE:FF AA:BB:CC:DD:EE:FF localhost 1812 my-secret-key-12345

# Test authentication for unknown client (should fail)
radtest -t pap 11:22:33:44:55:66 11:22:33:44:55:66 localhost 1812 my-secret-key-12345
```

### Expected results

- **Printer (00:11:22:33:44:55)**: Access-Accept with VLAN 100
- **Workstation (AA:BB:CC:DD:EE:FF)**: Access-Accept with VLAN 200
- **Unknown (11:22:33:44:55:66)**: Access-Reject

## Web UI Usage

Visit http://localhost:5000 to access the web interface:

### Devices Tab
- View all registered devices
- Add new devices
- Edit device details
- Delete devices

### Clients Tab
- View all registered clients (MAC addresses)
- Add new clients
- Assign clients to groups
- Delete clients

### Policies Tab
- View all authentication policies
- Create new policies
- Edit policy decisions and VLAN assignments
- Delete policies

### Logs Tab
- View authentication logs in real-time
- Filter by date range
- Filter by MAC address
- Filter by outcome (success/failure)
- Green indicator for successful authentications
- Red indicator for failed authentications

## Advanced Configuration

### Multiple Devices

```bash
# Add another switch
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-02",
    "ip_address": "192.168.1.101",
    "shared_secret": "another-secret-key-12345",
    "device_group_id": "access-layer"
  }'
```

### Policy Types

**Accept with VLAN:**
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "printers",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 100
  }'
```

**Accept without VLAN:**
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "guests",
    "decision": "ACCEPT_WITHOUT_VLAN"
  }'
```

**Reject:**
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "blocked",
    "decision": "REJECT"
  }'
```

## Troubleshooting

### Server won't start
```bash
# Check if port 1812 is already in use
sudo lsof -i :1812

# Check if port 5000 is already in use
sudo lsof -i :5000
```

### Authentication requests failing
1. Verify the device IP address matches the request source
2. Verify the shared secret is correct
3. Check the logs: `curl http://localhost:5000/api/logs`

### Can't connect to web UI
1. Verify the server is running: `ps aux | grep python3`
2. Check if port 5000 is accessible: `curl http://localhost:5000`
3. If on a remote machine, ensure firewall allows port 5000

## Data Persistence

All configuration and logs are automatically saved to:
- `/etc/radius-server/devices.json`
- `/etc/radius-server/clients.json`
- `/etc/radius-server/policies.json`
- `/etc/radius-server/logs.json`

These files persist across server restarts, so your configuration is safe.

## Next Steps

1. Configure your network devices to send RADIUS requests to this server
2. Test with real network equipment
3. Monitor logs for authentication events
4. Adjust policies as needed
5. Set up the systemd service for production use (see DEPLOYMENT_GUIDE.md)
