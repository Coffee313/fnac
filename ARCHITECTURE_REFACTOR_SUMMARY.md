# FNAC Architecture Refactor Summary

## What Changed

FNAC has been refactored from a **standalone RADIUS server** to a **management UI for FreeRADIUS**.

### Before
- FNAC implemented its own RADIUS protocol handler
- Handled all authentication directly
- Limited to MAB only
- Custom implementation of RADIUS protocol

### After
- FNAC is a **management and configuration interface**
- FreeRADIUS handles all RADIUS protocol operations
- Supports MAB now, PEAP/EAP-TLS in the future
- FNAC auto-generates FreeRADIUS configuration files
- Clean separation of concerns

## New Components

### 1. FreeRADIUS Config Generator (`src/freeradius_config_generator.py`)

Automatically generates FreeRADIUS configuration files:

- **`clients.conf`** - RADIUS clients (network devices)
- **`mab_users`** - MAC addresses with VLAN assignments

Features:
- Automatic config generation from FNAC data
- Backup of existing configs
- FreeRADIUS reload after updates
- Configuration validation

### 2. Updated API (`src/api.py`)

All endpoints remain the same, but now:
- Trigger FreeRADIUS config updates after changes
- Automatically reload FreeRADIUS when needed
- Maintain backward compatibility

### 3. Updated Main (`src/main.py`)

Now initializes:
- FreeRADIUS config generator
- Passes it to Flask app
- Enables automatic config updates

## Data Flow

### Configuration Update Flow
```
User updates device/client/policy in FNAC UI
         │
         ▼
    API endpoint receives request
         │
         ▼
    FNAC updates internal database
         │
         ▼
    Config generator creates FreeRADIUS files
         │
         ├─ /etc/freeradius/3.0/clients.conf
         └─ /etc/freeradius/3.0/mab_users
         │
         ▼
    FreeRADIUS reloads configuration
         │
         ▼
    Changes take effect immediately
```

### Authentication Flow
```
Network device sends RADIUS request (UDP 1812)
         │
         ▼
    FreeRADIUS receives request
         │
         ▼
    FreeRADIUS looks up client in mab_users
         │
         ▼
    FreeRADIUS evaluates policy (VLAN assignment)
         │
         ▼
    FreeRADIUS sends Access-Accept or Access-Reject
         │
         ▼
    FNAC logs authentication attempt (via API)
```

## Files Modified

1. **`src/api.py`**
   - Added FreeRADIUS config generator parameter
   - Added `_update_freeradius_config()` helper
   - Updated all POST/DELETE endpoints to trigger config updates

2. **`src/main.py`**
   - Added FreeRADIUS config generator initialization
   - Removed standalone RADIUS server startup
   - Passes config generator to Flask app

3. **`src/radius_server.py`**
   - No longer used (FreeRADIUS handles RADIUS protocol)
   - Kept for reference/testing

## Files Created

1. **`src/freeradius_config_generator.py`**
   - Generates FreeRADIUS configuration files
   - Manages config backups
   - Handles FreeRADIUS reload

2. **`FREERADIUS_INTEGRATION.md`**
   - Architecture overview
   - Integration details
   - Future enhancements

3. **`FREERADIUS_MAB_SETUP.md`**
   - Step-by-step FreeRADIUS setup
   - MAB configuration
   - Testing procedures
   - Troubleshooting

4. **`DEPLOYMENT_WITH_FREERADIUS.md`**
   - Complete deployment guide
   - Configuration steps
   - Testing procedures
   - Monitoring and troubleshooting

5. **`ARCHITECTURE_REFACTOR_SUMMARY.md`** (this file)
   - Summary of changes
   - Data flow diagrams
   - Migration guide

## Migration Guide

### For Existing Deployments

If you have FNAC already running:

1. **Stop FNAC**
   ```bash
   Ctrl+C
   ```

2. **Install FreeRADIUS**
   ```bash
   sudo apt-get install freeradius freeradius-utils
   ```

3. **Configure FreeRADIUS**
   - Follow `FREERADIUS_MAB_SETUP.md`

4. **Update FNAC**
   ```bash
   git pull origin main
   ```

5. **Start FNAC**
   ```bash
   sudo -E ./quickstart.sh run
   ```

6. **Reconfigure devices/clients/policies**
   - FNAC will auto-generate FreeRADIUS configs

### For New Deployments

1. Install FreeRADIUS first
2. Deploy FNAC
3. Configure via FNAC UI
4. Test with radtest

## Benefits

1. **Enterprise-grade authentication**
   - FreeRADIUS is battle-tested and production-ready
   - Supports multiple authentication methods

2. **Future-proof**
   - Easy to add PEAP/EAP-TLS support
   - FreeRADIUS handles complexity

3. **Clean separation**
   - FNAC focuses on management
   - FreeRADIUS focuses on authentication

4. **Easier maintenance**
   - Leverage FreeRADIUS community
   - Standard configuration format
   - Well-documented

5. **Better performance**
   - FreeRADIUS is optimized for RADIUS
   - Proven scalability

## Backward Compatibility

- All FNAC API endpoints remain unchanged
- Web UI is identical
- Data format is compatible
- Existing configurations can be migrated

## Next Steps

1. Deploy FreeRADIUS
2. Configure FNAC
3. Test MAB authentication
4. Plan for PEAP/EAP-TLS support (future)

## Support

For questions or issues:
1. Check `FREERADIUS_MAB_SETUP.md` for FreeRADIUS setup
2. Check `DEPLOYMENT_WITH_FREERADIUS.md` for deployment
3. Review FreeRADIUS logs: `/var/log/freeradius/radius.log`
4. Review FNAC logs: Check terminal output
