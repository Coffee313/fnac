# Quick Reference: Common Commands

## Setup & Running

```bash
# Initial setup (one-time)
./quickstart.sh setup

# Start the server
./quickstart.sh run

# Run tests
./quickstart.sh test

# Clean up
./quickstart.sh clean
```

## Device Management

### Create Device Group
```bash
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "access-layer", "name": "Access Layer Switches"}'
```

### Create Device
```bash
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key-12345",
    "device_group_id": "access-layer"
  }'
```

### List Devices
```bash
curl http://localhost:5000/api/devices | python3 -m json.tool
```

### Update Device
```bash
curl -X PUT http://localhost:5000/api/devices/switch-01 \
  -H "Content-Type: application/json" \
  -d '{
    "ip_address": "192.168.1.101",
    "shared_secret": "new-secret-key",
    "device_group_id": "access-layer"
  }'
```

### Delete Device
```bash
curl -X DELETE http://localhost:5000/api/devices/switch-01
```

## Client Management

### Create Client Group
```bash
curl -X POST http://localhost:5000/api/client-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "printers", "name": "Network Printers"}'
```

### Create Client
```bash
curl -X POST http://localhost:5000/api/clients \
  -H "Content-Type: application/json" \
  -d '{
    "mac_address": "00:11:22:33:44:55",
    "client_group_id": "printers"
  }'
```

### List Clients
```bash
curl http://localhost:5000/api/clients | python3 -m json.tool
```

### Update Client
```bash
curl -X PUT http://localhost:5000/api/clients/00:11:22:33:44:55 \
  -H "Content-Type: application/json" \
  -d '{"client_group_id": "workstations"}'
```

### Delete Client
```bash
curl -X DELETE http://localhost:5000/api/clients/00:11:22:33:44:55
```

## Policy Management

### Create Policy (Accept with VLAN)
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "printers",
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 100
  }'
```

### Create Policy (Accept without VLAN)
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "guests",
    "decision": "ACCEPT_WITHOUT_VLAN"
  }'
```

### Create Policy (Reject)
```bash
curl -X POST http://localhost:5000/api/policies \
  -H "Content-Type: application/json" \
  -d '{
    "client_group_id": "blocked",
    "decision": "REJECT"
  }'
```

### List Policies
```bash
curl http://localhost:5000/api/policies | python3 -m json.tool
```

### Update Policy
```bash
curl -X PUT http://localhost:5000/api/policies/policy-id \
  -H "Content-Type: application/json" \
  -d '{
    "decision": "ACCEPT_WITH_VLAN",
    "vlan_id": 200
  }'
```

### Delete Policy
```bash
curl -X DELETE http://localhost:5000/api/policies/policy-id
```

## Log Management

### List All Logs
```bash
curl http://localhost:5000/api/logs | python3 -m json.tool
```

### Filter by MAC Address
```bash
curl "http://localhost:5000/api/logs?mac_address=00:11:22:33:44:55" | python3 -m json.tool
```

### Filter by Outcome
```bash
# Successful authentications
curl "http://localhost:5000/api/logs?outcome=SUCCESS" | python3 -m json.tool

# Failed authentications
curl "http://localhost:5000/api/logs?outcome=FAILURE" | python3 -m json.tool
```

### Filter by Date Range
```bash
curl "http://localhost:5000/api/logs?date_start=2024-01-01&date_end=2024-01-31" | python3 -m json.tool
```

### Combine Filters
```bash
curl "http://localhost:5000/api/logs?mac_address=00:11:22:33:44:55&outcome=SUCCESS&date_start=2024-01-01" | python3 -m json.tool
```

## Testing

### Run All Tests
```bash
./quickstart.sh test
```

### Run Specific Test File
```bash
source venv/bin/activate
pytest tests/test_device_manager.py -v
```

### Run Tests with Coverage
```bash
source venv/bin/activate
pytest tests/ --cov=src --cov-report=html
```

### Run Property-Based Tests Only
```bash
source venv/bin/activate
pytest tests/ -v -k "property"
```

## Troubleshooting

### Check if Server is Running
```bash
ps aux | grep python3 | grep src.main
```

### Check Port Usage
```bash
# Check RADIUS port
sudo lsof -i :1812

# Check Web UI port
sudo lsof -i :5000
```

### View Configuration Files
```bash
# List all configuration files
ls -la /etc/radius-server/

# View devices
cat /etc/radius-server/devices.json | python3 -m json.tool

# View clients
cat /etc/radius-server/clients.json | python3 -m json.tool

# View policies
cat /etc/radius-server/policies.json | python3 -m json.tool

# View logs
cat /etc/radius-server/logs.json | python3 -m json.tool
```

### Activate Virtual Environment
```bash
source venv/bin/activate
```

### Deactivate Virtual Environment
```bash
deactivate
```

## RADIUS Testing (with radtest)

### Install radtest
```bash
sudo apt install -y freeradius-utils
```

### Test Authentication
```bash
# Format: radtest <username> <password> <server> <port> <secret>
radtest -t pap 00:11:22:33:44:55 00:11:22:33:44:55 localhost 1812 my-secret-key-12345
```

### Expected Responses
- **Access-Accept**: Client authenticated successfully
- **Access-Reject**: Client authentication failed

## Web UI Access

- **Main Dashboard**: http://localhost:5000
- **Devices**: http://localhost:5000/devices
- **Clients**: http://localhost:5000/clients
- **Policies**: http://localhost:5000/policies
- **Logs**: http://localhost:5000/logs

## Common Errors & Solutions

### "Permission denied" on port 1812
```bash
# Run with sudo
sudo -E ./quickstart.sh run
```

### "Address already in use"
```bash
# Find and kill the process
sudo lsof -i :1812
sudo kill -9 <PID>
```

### "ModuleNotFoundError"
```bash
# Activate virtual environment
source venv/bin/activate
```

### "Connection refused"
```bash
# Check if server is running
ps aux | grep python3

# Check if port is open
curl http://localhost:5000
```

## Data Backup

### Backup Configuration
```bash
cp -r /etc/radius-server /etc/radius-server.backup
```

### Restore Configuration
```bash
cp -r /etc/radius-server.backup /etc/radius-server
```

## Performance Monitoring

### Check Memory Usage
```bash
ps aux | grep python3 | grep src.main
```

### Monitor Logs in Real-Time
```bash
watch -n 1 'curl -s http://localhost:5000/api/logs | python3 -m json.tool | tail -20'
```

### Count Authentication Events
```bash
curl -s http://localhost:5000/api/logs | python3 -c "import sys, json; logs = json.load(sys.stdin); print(f'Total: {len(logs)}, Success: {sum(1 for l in logs if l[\"outcome\"] == \"SUCCESS\")}, Failed: {sum(1 for l in logs if l[\"outcome\"] == \"FAILURE\")}')"
```

## Useful Aliases

Add to your `.bashrc` or `.zshrc`:

```bash
# RADIUS server commands
alias radius-start='./quickstart.sh run'
alias radius-test='./quickstart.sh test'
alias radius-setup='./quickstart.sh setup'
alias radius-logs='curl -s http://localhost:5000/api/logs | python3 -m json.tool'
alias radius-devices='curl -s http://localhost:5000/api/devices | python3 -m json.tool'
alias radius-clients='curl -s http://localhost:5000/api/clients | python3 -m json.tool'
alias radius-policies='curl -s http://localhost:5000/api/policies | python3 -m json.tool'
```

Then use:
```bash
radius-start
radius-logs
radius-devices
```
