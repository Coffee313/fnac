# Radperf Performance Optimization Guide

## Issue: Slow Response with Radperf

When testing with `radperf` (1 stream, 100 requests), the system is slow. This guide helps identify and fix the bottleneck.

## Quick Diagnostics

### Run Diagnostic Script
```bash
chmod +x diagnose_performance.sh
./diagnose_performance.sh
```

This will show:
- FreeRADIUS status and configuration
- FNAC status
- Database performance settings
- System resources
- Network status
- Recent errors

## Common Bottlenecks

### 1. FreeRADIUS Thread Pool Too Small
**Symptom:** Requests queue up, slow responses

**Fix:**
```bash
# Edit /etc/freeradius/3.0/radiusd.conf
sudo nano /etc/freeradius/3.0/radiusd.conf

# Find and update thread pool:
thread pool {
    start_servers = 32
    max_servers = 256
    min_spare_servers = 8
    max_spare_servers = 32
    max_requests_per_server = 0
}

# Restart FreeRADIUS
sudo systemctl restart freeradius-server
```

### 2. SQLite Database Locked
**Symptom:** Timeouts, "database is locked" errors

**Fix:**
```bash
# Check current settings
sqlite3 fnac.db "PRAGMA journal_mode; PRAGMA synchronous; PRAGMA busy_timeout;"

# These should be set (already done by Phase 1):
# journal_mode = wal
# synchronous = 1 (NORMAL)
# busy_timeout = 5000

# If not, restart FNAC to apply optimizations
sudo systemctl restart radius-server
```

### 3. FNAC Not Running or Slow
**Symptom:** FreeRADIUS can't reach FNAC for policy lookups

**Fix:**
```bash
# Check if FNAC is running
ps aux | grep "python.*main"

# Check if listening on port 5000
netstat -tlnp | grep 5000

# Restart FNAC
sudo systemctl restart radius-server

# Check logs
journalctl -u radius-server -f
```

### 4. Network Latency
**Symptom:** Slow even with small requests

**Fix:**
```bash
# Test local RADIUS response
time radclient -c 1 127.0.0.1:1812 auth testing123 <<< "User-Name = aa:bb:cc:dd:ee:ff"

# Should be <10ms per request
# If >50ms, check system resources
```

## Performance Tuning

### FreeRADIUS Optimization

1. **Increase Thread Pool**
```
thread pool {
    start_servers = 64      # Increase from 32
    max_servers = 512       # Increase from 256
    min_spare_servers = 16  # Increase from 8
    max_spare_servers = 64  # Increase from 32
}
```

2. **Increase Socket Buffers**
```
listen {
    type = auth
    port = 1812
    ipaddr = *
    recv_buff = 131072     # 128KB (from 64KB)
    send_buff = 131072     # 128KB (from 64KB)
}
```

3. **Disable Unnecessary Modules**
```
# In /etc/freeradius/3.0/radiusd.conf
# Comment out unused modules:
# - ldap
# - sql (unless needed)
# - perl
# - python
# - exec
# - detail
# - linelog
```

### FNAC Optimization

1. **Increase Async Batch Size**
```python
# In src/main.py
AsyncLogWriter(batch_size=500, flush_interval=0.5)
```

2. **Increase Database Cache**
```bash
sqlite3 fnac.db "PRAGMA cache_size=20000;"
```

3. **Enable Memory-Mapped I/O**
```bash
sqlite3 fnac.db "PRAGMA mmap_size=100000000000;"
```

### System Optimization

1. **Increase File Descriptors**
```bash
# Edit /etc/security/limits.conf
sudo nano /etc/security/limits.conf

# Add:
* soft nofile 65536
* hard nofile 65536

# Apply:
ulimit -n 65536
```

2. **Increase Network Buffer**
```bash
# Edit /etc/sysctl.conf
sudo nano /etc/sysctl.conf

# Add:
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# Apply:
sudo sysctl -p
```

## Testing Performance

### Single Request Test
```bash
time radclient -c 1 127.0.0.1:1812 auth testing123 <<< "User-Name = aa:bb:cc:dd:ee:ff"
```

### Radperf Test (1 stream, 100 requests)
```bash
radperf -c 1 -n 100 -s 127.0.0.1:1812 -t 10 -u aa:bb:cc:dd:ee:ff -p testing123
```

### Expected Results
- **Before optimization**: 5-10 req/s
- **After Phase 1**: 50-100 req/s
- **After tuning**: 100-500 req/s

## Monitoring During Test

### Terminal 1: Run Radperf
```bash
radperf -c 1 -n 100 -s 127.0.0.1:1812 -t 10 -u aa:bb:cc:dd:ee:ff -p testing123
```

### Terminal 2: Monitor System
```bash
watch -n 1 'top -bn1 | head -10'
```

### Terminal 3: Monitor Database
```bash
watch -n 1 'sqlite3 fnac.db "SELECT COUNT(*) FROM auth_logs;"'
```

### Terminal 4: Monitor FreeRADIUS
```bash
tail -f /var/log/freeradius/radius.log | grep -E "Auth|Error"
```

## Troubleshooting

### Radperf Shows "No Response"
1. Check FreeRADIUS is running: `systemctl status freeradius-server`
2. Check port 1812 is listening: `netstat -tlnp | grep 1812`
3. Check firewall: `sudo ufw status`
4. Check logs: `tail -f /var/log/freeradius/radius.log`

### Radperf Shows Timeouts
1. Increase FreeRADIUS thread pool
2. Check system resources: `top`, `free -h`
3. Check database locks: `sqlite3 fnac.db "PRAGMA busy_timeout;"`
4. Restart FreeRADIUS: `sudo systemctl restart freeradius-server`

### Radperf Shows Slow Responses
1. Run diagnostic script: `./diagnose_performance.sh`
2. Check if FNAC is running: `ps aux | grep python`
3. Check database performance: `sqlite3 fnac.db "PRAGMA journal_mode;"`
4. Check system resources: `top`, `iostat`

## Expected Performance

### With Phase 1 Optimizations
- **Throughput**: 50-100 req/s (1 stream)
- **Latency**: 10-20ms per request
- **CPU**: 20-40% usage
- **Memory**: 100-200MB

### With Full Tuning
- **Throughput**: 100-500 req/s (1 stream)
- **Latency**: 2-10ms per request
- **CPU**: 40-60% usage
- **Memory**: 200-300MB

### With Multiple Streams
- **Throughput**: 1000+ req/s (10 streams)
- **Latency**: 1-5ms per request
- **CPU**: 60-80% usage
- **Memory**: 300-500MB

## Checklist

- [ ] Run diagnostic script
- [ ] Check FreeRADIUS thread pool
- [ ] Check SQLite settings (WAL, synchronous, cache)
- [ ] Check FNAC is running
- [ ] Check system resources
- [ ] Increase thread pool if needed
- [ ] Increase socket buffers if needed
- [ ] Disable unnecessary modules
- [ ] Test with radperf
- [ ] Monitor during test
- [ ] Verify performance improvement

## Next Steps

### For 100+ req/s
✅ Phase 1 optimizations are sufficient

### For 500+ req/s
- Increase FreeRADIUS thread pool to 512
- Increase socket buffers to 256KB
- Disable unnecessary modules
- Increase system file descriptors

### For 1000+ req/s
- Use multiple streams in radperf
- Consider Redis for logging (Phase 2)
- Consider PostgreSQL (Phase 3)
- Consider load balancing

## Support

For issues:
1. Run `./diagnose_performance.sh`
2. Check logs: `journalctl -u radius-server -f`
3. Check FreeRADIUS logs: `tail -f /var/log/freeradius/radius.log`
4. Test single request: `radclient -c 1 ...`
5. Monitor system: `top`, `iostat`, `netstat`
