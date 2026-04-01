# FreeRADIUS MAB (MAC Authentication Bypass) Setup Guide

## Prerequisites

- FreeRADIUS 3.0+ installed
- Astra Linux 1.7.5 or similar
- Root/sudo access

## Installation

```bash
sudo apt-get update
sudo apt-get install freeradius freeradius-utils
```

## Configuration for MAB

### Step 1: Create MAB Users File

Create `/etc/freeradius/3.0/mab_users`:

```
# MAB Users File
# Format: MAC-Address Cleartext-Password := "password"

# Example entries (add your MAB clients here)
00:11:22:33:44:55 Cleartext-Password := "mab"
AA:BB:CC:DD:EE:FF Cleartext-Password := "mab"
```

### Step 2: Configure FreeRADIUS for MAB

Edit `/etc/freeradius/3.0/sites-enabled/default`:

Find the `authorize` section and add:

```
authorize {
    # ... existing entries ...
    
    # MAB - Check if User-Name is a MAC address
    if (User-Name =~ /^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$/) {
        files
    }
    
    # ... rest of entries ...
}
```

### Step 3: Configure Clients

Edit `/etc/freeradius/3.0/clients.conf`:

Add your RADIUS clients (network devices):

```
client 192.168.1.1 {
    secret = "your_shared_secret_here"
    shortname = "switch_1"
    nastype = "cisco"
}

client 192.168.1.2 {
    secret = "another_secret"
    shortname = "ap_1"
    nastype = "aruba"
}
```

### Step 4: Enable MAB Module

Edit `/etc/freeradius/3.0/mods-enabled/files`:

Ensure the `files` module is configured:

```
files {
    usersfile = "${confdir}/mab_users"
    acctusersfile = "${confdir}/acct_users"
    compat = "4.0"
}
```

### Step 5: Test Configuration

```bash
# Check for syntax errors
sudo freeradius -X

# This will start FreeRADIUS in debug mode
# Look for "Ready to process requests" message
```

### Step 6: Start FreeRADIUS Service

```bash
# Stop debug mode (Ctrl+C)

# Start the service
sudo systemctl start freeradius

# Enable on boot
sudo systemctl enable freeradius

# Check status
sudo systemctl status freeradius
```

## Testing MAB

### Using radtest

```bash
# Test with a MAC address
radtest -t mschap 00:11:22:33:44:55 mab 127.0.0.1 1812 shared_secret

# Expected response:
# Sent Access-Request Id 123 from 127.0.0.1:xxxxx to 127.0.0.1:1812
# Received Access-Accept Id 123 from 127.0.0.1:1812
```

### Using radclient

```bash
# Create a test request file (test.txt)
User-Name = "00:11:22:33:44:55"
User-Password = "mab"
NAS-IP-Address = 192.168.1.1

# Send the request
radclient -x 127.0.0.1:1812 auth shared_secret < test.txt
```

## VLAN Assignment (Tunnel Attributes)

To assign VLANs in MAB responses, add to `/etc/freeradius/3.0/mab_users`:

```
# Assign MAC to VLAN 100
00:11:22:33:44:55 Cleartext-Password := "mab"
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-ID = "100"

# Assign MAC to VLAN 200
AA:BB:CC:DD:EE:FF Cleartext-Password := "mab"
    Tunnel-Type = VLAN,
    Tunnel-Medium-Type = IEEE-802,
    Tunnel-Private-Group-ID = "200"
```

## Logs

View FreeRADIUS logs:

```bash
# Real-time logs
sudo tail -f /var/log/freeradius/radius.log

# Debug mode (more verbose)
sudo freeradius -X
```

## Troubleshooting

### FreeRADIUS won't start
```bash
# Check for syntax errors
sudo freeradius -C

# Check logs
sudo journalctl -u freeradius -n 50
```

### Clients not authenticating
1. Verify MAC address format (XX:XX:XX:XX:XX:XX)
2. Check shared secret matches in clients.conf
3. Verify MAC is in mab_users file
4. Check firewall allows UDP 1812

### VLAN not assigned
1. Verify Tunnel attributes in mab_users
2. Check network device supports VLAN assignment
3. Verify VLAN ID is valid (1-4094)

## Integration with FNAC

FNAC will:
1. Read device/client/policy configuration
2. Generate `/etc/freeradius/3.0/mab_users` automatically
3. Generate `/etc/freeradius/3.0/clients.conf` automatically
4. Reload FreeRADIUS when configuration changes

See `FREERADIUS_INTEGRATION.md` for details.
