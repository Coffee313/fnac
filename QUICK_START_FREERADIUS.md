# Quick Start: FNAC + FreeRADIUS

## 5-Minute Setup

### 1. Install FreeRADIUS
```bash
sudo apt-get update
sudo apt-get install freeradius freeradius-utils
```

### 2. Start FreeRADIUS
```bash
sudo systemctl start freeradius
sudo systemctl enable freeradius
```

### 3. Deploy FNAC
```bash
git clone https://github.com/YOUR_USERNAME/fnac.git
cd fnac
./quickstart.sh setup
sudo -E ./quickstart.sh run
```

### 4. Open FNAC UI
```
http://server-ip:5000
```

### 5. Add Your First Device

**Devices Tab:**
1. Create Device Group: "Switches"
2. Add Device:
   - ID: `switch_1`
   - IP: `192.168.1.1` (your switch IP)
   - Secret: `test123`
   - Group: `Switches`

✅ FNAC automatically updates FreeRADIUS!

### 6. Add a Client (MAC Address)

**Clients Tab:**
1. Create Client Group: "Printers"
2. Add Client:
   - MAC: `00:11:22:33:44:55`
   - Group: `Printers`

✅ FNAC automatically updates FreeRADIUS!

### 7. Create a Policy

**Policies Tab:**
1. Create Policy:
   - ID: `printer_policy`
   - Client Group: `Printers`
   - Decision: `Accept with VLAN`
   - VLAN ID: `100`

✅ FNAC automatically updates FreeRADIUS!

### 8. Test It

```bash
# From the server
radtest -t mschap 00:11:22:33:44:55 mab 127.0.0.1 1812 test123

# Expected: Received Access-Accept
```

## What's Happening Behind the Scenes

1. You configure devices/clients/policies in FNAC UI
2. FNAC updates its internal database
3. FNAC generates FreeRADIUS config files:
   - `/etc/freeradius/3.0/clients.conf` (devices)
   - `/etc/freeradius/3.0/mab_users` (MACs + VLANs)
4. FNAC reloads FreeRADIUS
5. Network devices send RADIUS requests to FreeRADIUS
6. FreeRADIUS authenticates using FNAC-generated config
7. FNAC logs the authentication attempt

## Key Files

| File | Purpose |
|------|---------|
| `src/freeradius_config_generator.py` | Generates FreeRADIUS configs |
| `src/api.py` | REST API (triggers config updates) |
| `src/main.py` | Initializes config generator |
| `/etc/freeradius/3.0/clients.conf` | RADIUS clients (auto-generated) |
| `/etc/freeradius/3.0/mab_users` | MAC users (auto-generated) |

## Troubleshooting

### FreeRADIUS not responding
```bash
sudo systemctl status freeradius
sudo freeradius -X  # Debug mode
```

### Config not updating
```bash
# Check permissions
sudo ls -la /etc/freeradius/3.0/

# Check FNAC logs (in terminal)
# Look for "Updated /etc/freeradius/3.0/..."
```

### MAC not authenticating
1. Verify MAC format: `XX:XX:XX:XX:XX:XX`
2. Check MAC is in FNAC Clients
3. Check policy exists for client's group
4. Verify shared secret matches

## Next Steps

- Read `FREERADIUS_MAB_SETUP.md` for detailed FreeRADIUS config
- Read `DEPLOYMENT_WITH_FREERADIUS.md` for production setup
- Read `FREERADIUS_INTEGRATION.md` for architecture details

## Architecture

```
Your Network Device (Switch/AP)
         │
         ▼ (RADIUS on UDP 1812)
    FreeRADIUS
         │
         ├─ Reads: clients.conf (from FNAC)
         ├─ Reads: mab_users (from FNAC)
         └─ Sends: Accept/Reject
         
    FNAC UI (HTTP 5000)
         │
         ├─ Manage Devices
         ├─ Manage Clients (MACs)
         ├─ Manage Policies (VLANs)
         └─ View Logs
```

## That's It!

You now have:
- ✅ FreeRADIUS handling RADIUS protocol
- ✅ FNAC managing configuration
- ✅ Automatic config generation
- ✅ MAB authentication working
- ✅ VLAN assignment support
- ✅ Ready for PEAP/EAP-TLS in the future

Happy authenticating! 🔐
