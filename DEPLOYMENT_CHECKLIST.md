# RADIUS Server Deployment Checklist

Use this checklist to ensure your RADIUS server is properly deployed and configured on Astra Linux.

## Pre-Deployment (Before Setup)

- [ ] Astra Linux 1.7.5 (or compatible Debian-based system) is installed
- [ ] System has internet connection for downloading dependencies
- [ ] You have sudo/root access
- [ ] Project files are copied to the VM
- [ ] Terminal access is available
- [ ] At least 100MB free disk space
- [ ] UDP port 1812 is available (check: `sudo lsof -i :1812`)
- [ ] TCP port 5000 is available (check: `sudo lsof -i :5000`)

## System Preparation

- [ ] System packages updated: `sudo apt update && sudo apt upgrade -y`
- [ ] Python 3.8+ installed: `python3 --version`
- [ ] pip installed: `pip3 --version`
- [ ] venv module available: `python3 -m venv --help`
- [ ] curl installed (for testing): `which curl`
- [ ] Configuration directory created: `sudo mkdir -p /etc/radius-server`
- [ ] Configuration directory permissions set: `sudo chown $USER:$USER /etc/radius-server`

## Initial Setup

- [ ] Virtual environment created: `./quickstart.sh setup`
- [ ] Dependencies installed successfully
- [ ] No errors during setup
- [ ] Virtual environment activates: `source venv/bin/activate`
- [ ] Python packages installed: `pip list | grep -E "pyrad|flask|pytest|hypothesis"`

## Server Startup

- [ ] Server starts without errors: `./quickstart.sh run`
- [ ] RADIUS listener on UDP 1812 is active
- [ ] Web UI on HTTP 5000 is accessible
- [ ] No port conflicts
- [ ] Server logs show successful initialization

## Initial Configuration

- [ ] Device group created via API
- [ ] Device added with valid IP and shared secret
- [ ] Client group created via API
- [ ] Client (MAC address) added
- [ ] Policy created for client group
- [ ] All configuration persisted to `/etc/radius-server/`

## Testing

- [ ] Unit tests pass: `./quickstart.sh test`
- [ ] All test files execute without errors
- [ ] Property-based tests complete successfully
- [ ] No test failures or warnings
- [ ] Integration tests pass

## Web UI Verification

- [ ] Web UI accessible at http://localhost:5000
- [ ] Devices tab shows created devices
- [ ] Clients tab shows added clients
- [ ] Policies tab shows created policies
- [ ] Logs tab displays authentication events
- [ ] Visual indicators (green/red) work correctly

## API Verification

- [ ] GET /api/devices returns device list
- [ ] GET /api/clients returns client list
- [ ] GET /api/policies returns policy list
- [ ] GET /api/logs returns authentication logs
- [ ] POST endpoints create new entries
- [ ] PUT endpoints update existing entries
- [ ] DELETE endpoints remove entries
- [ ] Error responses are descriptive

## Data Persistence

- [ ] `/etc/radius-server/devices.json` exists and contains data
- [ ] `/etc/radius-server/clients.json` exists and contains data
- [ ] `/etc/radius-server/policies.json` exists and contains data
- [ ] `/etc/radius-server/logs.json` exists and contains data
- [ ] JSON files are valid and readable
- [ ] Data survives server restart

## RADIUS Protocol Testing (Optional)

- [ ] freeradius-utils installed: `sudo apt install -y freeradius-utils`
- [ ] radtest tool available: `which radtest`
- [ ] Test authentication succeeds for known client
- [ ] Test authentication fails for unknown client
- [ ] VLAN assignment appears in response
- [ ] Authentication logs record test events

## Production Deployment (Optional)

- [ ] Systemd service file created: `/etc/systemd/system/radius-server.service`
- [ ] radius user created: `sudo useradd -r -s /bin/false radius`
- [ ] Configuration directory ownership set: `sudo chown -R radius:radius /etc/radius-server`
- [ ] Service enabled: `sudo systemctl enable radius-server`
- [ ] Service started: `sudo systemctl start radius-server`
- [ ] Service status is active: `sudo systemctl status radius-server`
- [ ] Service logs are accessible: `sudo journalctl -u radius-server`
- [ ] Service auto-restarts on failure
- [ ] Service starts on system boot

## Security Hardening

- [ ] Shared secrets are strong (16+ characters)
- [ ] Configuration files have restricted permissions (600)
- [ ] Server runs as unprivileged user (radius)
- [ ] Firewall rules restrict access to ports 1812 and 5000
- [ ] Only authorized devices can send RADIUS requests
- [ ] Logs are monitored for suspicious activity
- [ ] Regular backups of configuration files

## Monitoring & Maintenance

- [ ] Monitoring script created to check service status
- [ ] Log rotation configured (if using systemd)
- [ ] Backup strategy implemented
- [ ] Documentation updated with deployment details
- [ ] Team trained on configuration and troubleshooting
- [ ] Runbook created for common operations
- [ ] Escalation procedures documented

## Performance Verification

- [ ] Server responds to requests within acceptable time
- [ ] Memory usage is reasonable (< 100MB)
- [ ] CPU usage is low during idle
- [ ] No memory leaks observed over time
- [ ] Handles multiple concurrent requests
- [ ] Log file size is manageable

## Documentation

- [ ] README.md reviewed and understood
- [ ] GETTING_STARTED.md followed successfully
- [ ] EXAMPLE_SETUP.md examples tested
- [ ] DEPLOYMENT_GUIDE.md reviewed
- [ ] QUICK_REFERENCE.md bookmarked
- [ ] ARCHITECTURE.md understood
- [ ] Custom documentation created for your environment

## Troubleshooting Preparation

- [ ] Troubleshooting guide reviewed
- [ ] Common error messages documented
- [ ] Recovery procedures tested
- [ ] Backup restoration tested
- [ ] Support contacts identified
- [ ] Escalation procedures documented

## Sign-Off

- [ ] All checklist items completed
- [ ] System tested and verified working
- [ ] Documentation complete
- [ ] Team trained and ready
- [ ] Deployment approved by management
- [ ] Go-live date scheduled

---

## Quick Verification Commands

Run these commands to verify your deployment:

```bash
# Check if server is running
ps aux | grep python3 | grep src.main

# Check port availability
sudo lsof -i :1812
sudo lsof -i :5000

# Test API connectivity
curl http://localhost:5000/api/devices

# View configuration files
ls -la /etc/radius-server/

# Check service status (if using systemd)
sudo systemctl status radius-server

# View recent logs
curl http://localhost:5000/api/logs | python3 -m json.tool | head -20

# Run tests
./quickstart.sh test
```

## Rollback Procedure

If something goes wrong:

1. Stop the server: `Ctrl+C` or `sudo systemctl stop radius-server`
2. Restore from backup: `cp -r /etc/radius-server.backup /etc/radius-server`
3. Restart the server: `./quickstart.sh run` or `sudo systemctl start radius-server`
4. Verify restoration: `curl http://localhost:5000/api/devices`

## Next Steps After Deployment

1. Configure network devices to send RADIUS requests to this server
2. Test with real network equipment
3. Monitor logs for authentication events
4. Adjust policies as needed
5. Set up monitoring and alerting
6. Schedule regular backups
7. Plan for capacity and scaling

---

**Deployment Date**: _______________

**Deployed By**: _______________

**Verified By**: _______________

**Notes**: 
```
_________________________________________________________________

_________________________________________________________________

_________________________________________________________________
```
