# 🚀 START HERE

Welcome to the Simple RADIUS Server! This is your entry point to getting the server running on your Astra Linux VM.

## What is This?

A fully functional RADIUS server that:
- Authenticates network devices by MAC address
- Assigns VLANs based on policies
- Logs all authentication events
- Provides a web interface for configuration
- Persists all data across restarts

## Quick Start (10 minutes)

### 1. Prepare Your System
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv curl
```

### 2. Setup the Server
```bash
cd /path/to/simple-radius-server
./quickstart.sh setup
```

### 3. Start the Server
```bash
./quickstart.sh run
```

### 4. Configure Your First Device (in another terminal)
```bash
# Create device group
curl -X POST http://localhost:5000/api/device-groups \
  -H "Content-Type: application/json" \
  -d '{"id": "switches", "name": "Network Switches"}'

# Add device
curl -X POST http://localhost:5000/api/devices \
  -H "Content-Type: application/json" \
  -d '{
    "id": "switch-01",
    "ip_address": "192.168.1.100",
    "shared_secret": "my-secret-key-12345",
    "device_group_id": "switches"
  }'
```

### 5. Open the Web UI
```
http://localhost:5000
```

**Done!** Your RADIUS server is running. 🎉

---

## Documentation Guide

### 📖 Read These First
1. **[VISUAL_QUICKSTART.txt](VISUAL_QUICKSTART.txt)** - Visual step-by-step guide
2. **[GETTING_STARTED.md](GETTING_STARTED.md)** - Detailed setup guide
3. **[EXAMPLE_SETUP.md](EXAMPLE_SETUP.md)** - Configuration examples

### 📚 Reference
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common commands
- **[README.md](README.md)** - Full documentation
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design

### 🔧 Production
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Production setup
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Verification

### 📋 Index
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - All docs overview

---

## What's Included

```
simple-radius-server/
├── src/                    # Python source code
├── tests/                  # Test suite
├── requirements.txt        # Dependencies
├── quickstart.sh          # Setup script
├── README.md              # Full docs
├── GETTING_STARTED.md     # Setup guide
├── EXAMPLE_SETUP.md       # Examples
├── DEPLOYMENT_GUIDE.md    # Production
├── QUICK_REFERENCE.md     # Commands
├── ARCHITECTURE.md        # Design
└── ... (more docs)
```

---

## Key Features

✅ **RFC 2865 Compliant** - Standard RADIUS protocol  
✅ **MAC Authentication** - Authenticate by MAC address  
✅ **Policy-Based** - Define access rules  
✅ **VLAN Assignment** - Automatic VLAN assignment  
✅ **Web UI** - Easy configuration interface  
✅ **REST API** - Programmatic access  
✅ **Logging** - Complete audit trail  
✅ **Persistent** - Data survives restarts  
✅ **Tested** - 44 correctness properties  

---

## System Requirements

- Astra Linux 1.7.5 (or any Debian-based system)
- Python 3.8+
- 100MB disk space
- UDP port 1812 (RADIUS)
- TCP port 5000 (Web UI)

---

## Common Tasks

### View Logs
```bash
curl http://localhost:5000/api/logs | python3 -m json.tool
```

### List Devices
```bash
curl http://localhost:5000/api/devices | python3 -m json.tool
```

### Run Tests
```bash
./quickstart.sh test
```

### Stop Server
```bash
# Press Ctrl+C in the server terminal
```

---

## Troubleshooting

### "Permission denied" on port 1812
The script handles this automatically with `sudo`.

### "Address already in use"
```bash
sudo lsof -i :1812
sudo kill -9 <PID>
```

### "ModuleNotFoundError"
```bash
source venv/bin/activate
```

### Can't access web UI
```bash
ps aux | grep python3 | grep src.main
```

---

## Next Steps

1. ✅ **Setup** - Follow [GETTING_STARTED.md](GETTING_STARTED.md)
2. 📖 **Learn** - Read [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md)
3. 🔧 **Configure** - Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
4. 🚀 **Deploy** - Follow [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## File Structure

| File | Purpose | Read Time |
|------|---------|-----------|
| VISUAL_QUICKSTART.txt | Visual guide | 5 min |
| GETTING_STARTED.md | Setup guide | 10 min |
| EXAMPLE_SETUP.md | Examples | 15 min |
| QUICK_REFERENCE.md | Commands | 15 min |
| README.md | Full docs | 20 min |
| ARCHITECTURE.md | Design | 25 min |
| DEPLOYMENT_GUIDE.md | Production | 30 min |
| DEPLOYMENT_CHECKLIST.md | Verification | 10 min |

---

## Quick Commands

```bash
# Setup
./quickstart.sh setup

# Run
./quickstart.sh run

# Test
./quickstart.sh test

# Clean
./quickstart.sh clean

# View logs
curl http://localhost:5000/api/logs | python3 -m json.tool

# List devices
curl http://localhost:5000/api/devices | python3 -m json.tool

# Web UI
http://localhost:5000
```

---

## Support

- **Setup issues?** → [GETTING_STARTED.md](GETTING_STARTED.md)
- **Need examples?** → [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md)
- **Need commands?** → [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **Need architecture?** → [ARCHITECTURE.md](ARCHITECTURE.md)
- **Going to production?** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Need verification?** → [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)

---

## Success Indicators

You'll know it's working when:

✓ Server starts without errors  
✓ Web UI accessible at http://localhost:5000  
✓ Can create devices via API  
✓ Can create clients via API  
✓ Can create policies via API  
✓ Logs appear in the log viewer  
✓ Tests pass: `./quickstart.sh test`  

---

## What Happens Next

1. **Server listens** on UDP 1812 for RADIUS requests
2. **Devices send** authentication requests
3. **Server verifies** device by IP and shared secret
4. **Server extracts** client MAC address
5. **Server looks up** client and policy
6. **Server responds** with Accept/Reject + VLAN
7. **Server logs** the authentication event
8. **You monitor** logs in the web UI

---

## Ready to Start?

### Option 1: Quick Start (5 minutes)
```bash
./quickstart.sh setup
./quickstart.sh run
# Open http://localhost:5000
```

### Option 2: Guided Setup (15 minutes)
Read [GETTING_STARTED.md](GETTING_STARTED.md) and follow along

### Option 3: Visual Guide (10 minutes)
Read [VISUAL_QUICKSTART.txt](VISUAL_QUICKSTART.txt)

---

## Key Concepts

**Device**: Network equipment (switch, AP) that sends RADIUS requests  
**Client**: End device identified by MAC address  
**Policy**: Rule that determines Accept/Reject/VLAN assignment  
**Log**: Record of authentication attempt  

---

## Data Storage

All configuration is stored in JSON files:
```
/etc/radius-server/
├── devices.json
├── clients.json
├── policies.json
└── logs.json
```

These persist across server restarts.

---

## Production Deployment

When ready for production:
1. Read [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
2. Follow [DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)
3. Set up systemd service
4. Configure monitoring
5. Set up backups

---

## Questions?

- **How do I...?** → Check [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
- **What is...?** → Check [README.md](README.md) or [ARCHITECTURE.md](ARCHITECTURE.md)
- **How do I set up...?** → Check [EXAMPLE_SETUP.md](EXAMPLE_SETUP.md)
- **How do I deploy...?** → Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

---

## Let's Go! 🚀

```bash
cd /path/to/simple-radius-server
./quickstart.sh setup
./quickstart.sh run
```

Then open: http://localhost:5000

**Enjoy your RADIUS server!**

---

**Next**: Read [GETTING_STARTED.md](GETTING_STARTED.md) or [VISUAL_QUICKSTART.txt](VISUAL_QUICKSTART.txt)
