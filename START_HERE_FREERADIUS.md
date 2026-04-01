# 🚀 START HERE: FNAC + FreeRADIUS

Welcome! This guide will get you up and running in **5 minutes**.

## What is FNAC?

FNAC is a **web-based management interface** for FreeRADIUS that lets you:
- 🔐 Authenticate network devices by MAC address (MAB)
- 🏢 Assign VLANs automatically
- 📊 Monitor authentication in real-time
- ⚙️ Manage everything from a simple web UI

## What You'll Have

```
Your Network Device (Switch/AP)
         │
         ▼ (sends RADIUS request)
    FreeRADIUS (UDP 1812)
         │
         ├─ Authenticates MAC address
         ├─ Assigns VLAN
         └─ Sends response
         
    FNAC Web UI (HTTP 5000)
         │
         ├─ Add devices
         ├─ Add MAC addresses
         ├─ Create policies
         └─ View logs
```

## 5-Minute Setup

### Step 1: Install FreeRADIUS (1 minute)
```bash
sudo apt-get update
sudo apt-get install freeradius freeradius-utils
sudo systemctl start freeradius
```

### Step 2: Deploy FNAC (2 minutes)
```bash
git clone https://github.com/YOUR_USERNAME/fnac.git
cd fnac
./quickstart.sh setup
sudo -E ./quickstart.sh run
```

### Step 3: Open Web UI (1 minute)
```
Open browser: http://server-ip:5000
```

### Step 4: Configure (1 minute)
1. **Devices Tab**: Add your switch/AP
2. **Clients Tab**: Add a MAC address
3. **Policies Tab**: Create a policy with VLAN assignment

## Testing (Optional)

```bash
# Test authentication
radtest -t mschap 00:11:22:33:44:55 mab 127.0.0.1 1812 shared_secret

# Expected: Received Access-Accept
```

## What Happens Automatically

When you add a device/client/policy in FNAC:

1. ✅ FNAC updates its database
2. ✅ Config generator creates FreeRADIUS files
3. ✅ FreeRADIUS reloads automatically
4. ✅ Changes take effect immediately

**No manual FreeRADIUS configuration needed!**

## Documentation

Read these in order:

1. **[Quick Start](QUICK_START_FREERADIUS.md)** - Detailed 5-minute setup
2. **[Deployment Checklist](DEPLOYMENT_CHECKLIST_FREERADIUS.md)** - Step-by-step checklist
3. **[FreeRADIUS Setup](FREERADIUS_MAB_SETUP.md)** - If you need FreeRADIUS details
4. **[Complete Guide](FNAC_FREERADIUS_COMPLETE.md)** - Full reference

## Common Tasks

### Add a Device (Switch/AP)
1. Go to **Devices** tab
2. Create a Device Group (e.g., "Switches")
3. Add Device:
   - ID: `switch_1`
   - IP: `192.168.1.1` (your switch IP)
   - Secret: `test123`
   - Group: `Switches`

### Add a Client (MAC Address)
1. Go to **Clients** tab
2. Create a Client Group (e.g., "Printers")
3. Add Client:
   - MAC: `00:11:22:33:44:55`
   - Group: `Printers`

### Create a Policy (VLAN Assignment)
1. Go to **Policies** tab
2. Create Policy:
   - ID: `printer_policy`
   - Client Group: `Printers`
   - Decision: `Accept with VLAN`
   - VLAN ID: `100`

### View Logs
1. Go to **Logs** tab
2. See all authentication attempts
3. Filter by MAC or outcome

## Troubleshooting

### FreeRADIUS not responding?
```bash
sudo systemctl status freeradius
sudo freeradius -X  # Debug mode
```

### Config not updating?
```bash
# Check permissions
sudo ls -la /etc/freeradius/3.0/

# Check FNAC logs (in terminal)
```

### MAC not authenticating?
1. Verify MAC format: `XX:XX:XX:XX:XX:XX`
2. Check MAC is in FNAC Clients
3. Check policy exists
4. Verify shared secret matches

## System Requirements

- **OS**: Astra Linux 1.7.5+ or similar
- **Python**: 3.7+
- **FreeRADIUS**: 3.0+
- **Ports**: 5000 (HTTP), 1812 (UDP)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  FNAC Web UI (5000)                     │
│  - Device Management                                    │
│  - Client Management (MAC addresses)                    │
│  - Policy Management (VLAN assignments)                 │
│  - Authentication Logs                                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  Config Generator          │
        │  - clients.conf            │
        │  - mab_users               │
        │  - FreeRADIUS reload       │
        └────────────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │      FreeRADIUS (UDP 1812)         │
        │  - RADIUS protocol handler         │
        │  - MAB authentication              │
        │  - VLAN assignment                 │
        │  - Event logging                   │
        └────────────────────────────────────┘
```

## Key Features

✅ **MAB Authentication** - Authenticate by MAC address
✅ **VLAN Assignment** - Automatically assign VLANs
✅ **Web UI** - Simple, intuitive interface
✅ **Auto-Config** - Automatic FreeRADIUS configuration
✅ **Real-Time Logs** - Monitor authentication attempts
✅ **Enterprise-Grade** - Powered by FreeRADIUS
✅ **Future-Ready** - Ready for PEAP/EAP-TLS

## Next Steps

1. **Deploy** - Follow the 5-minute setup above
2. **Configure** - Add devices, clients, policies
3. **Test** - Use radtest or network device
4. **Monitor** - Check logs in FNAC UI
5. **Plan** - Consider 802.1X support for future

## Support

- 📖 Check the documentation
- 🔍 Review FreeRADIUS logs: `/var/log/freeradius/radius.log`
- 🔍 Review FNAC logs: Check terminal output
- 🧪 Test with radtest: `radtest -t mschap MAC mab 127.0.0.1 1812 secret`

## Quick Links

- [Quick Start](QUICK_START_FREERADIUS.md)
- [Deployment Checklist](DEPLOYMENT_CHECKLIST_FREERADIUS.md)
- [FreeRADIUS Setup](FREERADIUS_MAB_SETUP.md)
- [Complete Guide](FNAC_FREERADIUS_COMPLETE.md)
- [Architecture](FREERADIUS_INTEGRATION.md)

---

**Ready to get started?** Follow the 5-minute setup above! 🚀

**Questions?** Check the documentation or review the logs.

**Happy authenticating!** 🔐
