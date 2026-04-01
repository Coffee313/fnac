# FNAC + FreeRADIUS Integration Architecture

## Overview

FNAC is now a **management and configuration UI** for FreeRADIUS. The architecture is:

```
┌─────────────────────────────────────────────────────────────┐
│                    FNAC Web UI (Port 5000)                  │
│  - Device Management                                        │
│  - Client Management (MAC addresses)                        │
│  - Policy Management (VLAN assignment)                      │
│  - Authentication Logs                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
        ┌────────────────────────────┐
        │  FNAC Configuration Engine │
        │  - Generates FreeRADIUS    │
        │    config files            │
        │  - Manages policies        │
        │  - Tracks authentication   │
        └────────────────┬───────────┘
                         │
                         ▼
        ┌────────────────────────────────────┐
        │      FreeRADIUS Server             │
        │  - UDP 1812 (RADIUS)               │
        │  - Handles MAB, PEAP, EAP-TLS      │
        │  - Reads FNAC config               │
        └────────────────────────────────────┘
```

## Components

### 1. FreeRADIUS (Authentication Engine)
- Handles all RADIUS protocol operations
- Supports MAB (MAC Authentication Bypass)
- Supports 802.1X (PEAP, EAP-TLS) - future
- Listens on UDP 1812

### 2. FNAC (Management UI)
- Web interface on HTTP 5000
- Manages configuration
- Generates FreeRADIUS config files
- Tracks authentication logs
- Manages device/client/policy database

### 3. Configuration Files
- FreeRADIUS config: `/etc/freeradius/3.0/`
- FNAC data: `./data/` (JSON files)
- Generated configs: `./freeradius_config/` (auto-generated)

## Setup Steps

### Step 1: Install FreeRADIUS
```bash
sudo apt-get update
sudo apt-get install freeradius freeradius-utils
```

### Step 2: Configure FreeRADIUS for MAB
See `FREERADIUS_MAB_SETUP.md`

### Step 3: Deploy FNAC
```bash
git clone https://github.com/YOUR_USERNAME/fnac.git
cd fnac
./quickstart.sh setup
sudo -E ./quickstart.sh run
```

### Step 4: Access FNAC UI
- Open browser: `http://server-ip:5000`
- Configure devices, clients, and policies
- FNAC automatically updates FreeRADIUS config

## Data Flow

### Authentication Request
1. Network device sends RADIUS Access-Request (UDP 1812)
2. FreeRADIUS receives request
3. FreeRADIUS queries FNAC database (via API or config files)
4. FreeRADIUS returns Access-Accept or Access-Reject
5. FNAC logs the authentication attempt

### Configuration Update
1. User updates device/client/policy in FNAC UI
2. FNAC updates internal database
3. FNAC generates FreeRADIUS config files
4. FreeRADIUS reloads configuration
5. Changes take effect immediately

## API Endpoints (FNAC)

All endpoints remain the same:
- `GET /api/devices` - List devices
- `POST /api/devices` - Create device
- `GET /api/clients` - List clients
- `POST /api/clients` - Create client
- `GET /api/policies` - List policies
- `POST /api/policies` - Create policy
- `GET /api/logs` - View authentication logs

## Configuration Files Generated

FNAC generates these FreeRADIUS config files:

### 1. `clients.conf`
```
client 192.168.1.1 {
    secret = "shared_secret_here"
    shortname = "device_id"
}
```

### 2. `mab.conf`
```
# MAB policy configuration
# Maps MAC addresses to VLAN assignments
```

### 3. `users`
```
# User database (for future 802.1X support)
```

## Future Enhancements

- PEAP/EAP-TLS support (FreeRADIUS handles, FNAC manages certs)
- Real-time log streaming
- Advanced policy rules
- User authentication for FNAC UI
- Backup/restore functionality

## Troubleshooting

See `FREERADIUS_TROUBLESHOOTING.md`
