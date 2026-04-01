# FNAC + FreeRADIUS Deployment Checklist

## Pre-Deployment

- [ ] Review `QUICK_START_FREERADIUS.md`
- [ ] Review `FREERADIUS_MAB_SETUP.md`
- [ ] Verify system requirements (Python 3.7+, Astra Linux)
- [ ] Ensure sudo access available
- [ ] Plan IP addresses and shared secrets
- [ ] Identify network devices (switches, APs) to configure

## FreeRADIUS Installation

- [ ] Install FreeRADIUS: `sudo apt-get install freeradius freeradius-utils`
- [ ] Verify installation: `freeradius -v`
- [ ] Check FreeRADIUS config directory: `/etc/freeradius/3.0/`
- [ ] Start FreeRADIUS: `sudo systemctl start freeradius`
- [ ] Enable on boot: `sudo systemctl enable freeradius`
- [ ] Verify running: `sudo systemctl status freeradius`

## FNAC Deployment

- [ ] Clone repository: `git clone https://github.com/YOUR_USERNAME/fnac.git`
- [ ] Navigate to directory: `cd fnac`
- [ ] Run setup: `./quickstart.sh setup`
- [ ] Verify dependencies installed
- [ ] Start FNAC: `sudo -E ./quickstart.sh run`
- [ ] Verify FNAC is running (check terminal output)

## FNAC Web UI Access

- [ ] Open browser: `http://server-ip:5000`
- [ ] Verify web UI loads
- [ ] Check all tabs are accessible:
  - [ ] Devices tab
  - [ ] Clients tab
  - [ ] Policies tab
  - [ ] Logs tab

## Device Configuration

- [ ] Create Device Group (e.g., "Switches")
  - [ ] Group ID: `switches`
  - [ ] Group Name: `Switches`
- [ ] Add first device:
  - [ ] Device ID: `switch_1`
  - [ ] IP Address: `192.168.1.1` (your switch IP)
  - [ ] Shared Secret: `test123` (or your secret)
  - [ ] Device Group: `Switches`
- [ ] Verify device appears in list
- [ ] Check FreeRADIUS config updated:
  ```bash
  sudo grep "192.168.1.1" /etc/freeradius/3.0/clients.conf
  ```

## Client Configuration

- [ ] Create Client Group (e.g., "Printers")
  - [ ] Group ID: `printers`
  - [ ] Group Name: `Printers`
- [ ] Add first client:
  - [ ] MAC Address: `00:11:22:33:44:55` (test MAC)
  - [ ] Client Group: `Printers`
- [ ] Verify client appears in list
- [ ] Check FreeRADIUS config updated:
  ```bash
  sudo grep "00:11:22:33:44:55" /etc/freeradius/3.0/mab_users
  ```

## Policy Configuration

- [ ] Create policy:
  - [ ] Policy ID: `printer_policy`
  - [ ] Client Group: `Printers`
  - [ ] Decision: `Accept with VLAN`
  - [ ] VLAN ID: `100`
- [ ] Verify policy appears in list
- [ ] Check FreeRADIUS config updated:
  ```bash
  sudo grep -A 3 "00:11:22:33:44:55" /etc/freeradius/3.0/mab_users
  ```

## Testing

### Basic Connectivity
- [ ] Ping FreeRADIUS server: `ping server-ip`
- [ ] Verify UDP 1812 is open: `sudo netstat -ulnp | grep 1812`
- [ ] Verify HTTP 5000 is open: `sudo netstat -tlnp | grep 5000`

### RADIUS Testing
- [ ] Test with radtest:
  ```bash
  radtest -t mschap 00:11:22:33:44:55 mab 127.0.0.1 1812 test123
  ```
- [ ] Expected response: `Received Access-Accept`
- [ ] Check FreeRADIUS logs:
  ```bash
  sudo tail -f /var/log/freeradius/radius.log
  ```

### FNAC Logging
- [ ] Go to Logs tab in FNAC UI
- [ ] Verify authentication attempt appears
- [ ] Check MAC address matches
- [ ] Check outcome is "success"

## Network Device Configuration

- [ ] Configure network device (switch/AP):
  - [ ] RADIUS Server: `server-ip`
  - [ ] RADIUS Port: `1812`
  - [ ] Shared Secret: `test123` (must match FNAC config)
- [ ] Enable MAB on network device
- [ ] Test authentication from network device
- [ ] Verify device gets assigned to VLAN 100

## Monitoring

- [ ] Set up log monitoring:
  ```bash
  sudo tail -f /var/log/freeradius/radius.log
  ```
- [ ] Monitor FNAC logs (in terminal)
- [ ] Check FNAC Logs tab regularly
- [ ] Verify authentication attempts are logged

## Troubleshooting

### If FreeRADIUS won't start
- [ ] Check syntax: `sudo freeradius -C`
- [ ] Check logs: `sudo journalctl -u freeradius -n 50`
- [ ] Try debug mode: `sudo freeradius -X`

### If FNAC won't start
- [ ] Check Python version: `python3 --version`
- [ ] Check dependencies: `pip list`
- [ ] Check permissions: `sudo ls -la /etc/freeradius/3.0/`

### If config not updating
- [ ] Verify FNAC running with sudo: `ps aux | grep python`
- [ ] Check FNAC logs for errors
- [ ] Verify FreeRADIUS permissions:
  ```bash
  sudo ls -la /etc/freeradius/3.0/clients.conf
  sudo ls -la /etc/freeradius/3.0/mab_users
  ```

### If MAC not authenticating
- [ ] Verify MAC format: `XX:XX:XX:XX:XX:XX`
- [ ] Check MAC in FNAC Clients
- [ ] Check policy exists
- [ ] Verify shared secret matches
- [ ] Check FreeRADIUS config:
  ```bash
  sudo grep "MAC_ADDRESS" /etc/freeradius/3.0/mab_users
  ```

## Post-Deployment

- [ ] Document configuration (devices, clients, policies)
- [ ] Create backup of FNAC data:
  ```bash
  cp -r ./data ./data.backup
  ```
- [ ] Set up monitoring/alerting
- [ ] Plan for future 802.1X support
- [ ] Schedule regular backups
- [ ] Document troubleshooting procedures

## Production Readiness

- [ ] All tests passing
- [ ] Logs being generated correctly
- [ ] Network devices authenticating successfully
- [ ] VLAN assignments working
- [ ] Backup procedures in place
- [ ] Monitoring in place
- [ ] Documentation complete
- [ ] Team trained on FNAC UI

## Sign-Off

- [ ] Deployment completed by: ________________
- [ ] Date: ________________
- [ ] Verified by: ________________
- [ ] Date: ________________

## Notes

```
[Add any deployment notes, issues encountered, or special configurations here]
```

---

**Deployment Status**: ☐ Not Started | ☐ In Progress | ☐ Complete

**Next Steps**:
1. [ ] Monitor system for 24 hours
2. [ ] Verify all devices authenticating
3. [ ] Plan for 802.1X support
4. [ ] Schedule regular maintenance
