#!/bin/bash
# Performance diagnostic script for FNAC + FreeRADIUS

echo "=========================================="
echo "FNAC + FreeRADIUS Performance Diagnostics"
echo "=========================================="

echo ""
echo "1. Check FreeRADIUS Status"
echo "=========================================="
systemctl status freeradius-server 2>/dev/null || echo "FreeRADIUS not running as service"
ps aux | grep -i radius | grep -v grep

echo ""
echo "2. Check FreeRADIUS Configuration"
echo "=========================================="
echo "Thread pool settings:"
grep -A 10 "thread pool" /etc/freeradius/3.0/radiusd.conf 2>/dev/null | head -15

echo ""
echo "3. Check FNAC Status"
echo "=========================================="
ps aux | grep -i "python.*main" | grep -v grep

echo ""
echo "4. Check Database Performance"
echo "=========================================="
echo "SQLite WAL mode:"
sqlite3 fnac.db "PRAGMA journal_mode;" 2>/dev/null

echo "SQLite cache size:"
sqlite3 fnac.db "PRAGMA cache_size;" 2>/dev/null

echo "SQLite synchronous mode:"
sqlite3 fnac.db "PRAGMA synchronous;" 2>/dev/null

echo "Log count:"
sqlite3 fnac.db "SELECT COUNT(*) FROM auth_logs;" 2>/dev/null

echo ""
echo "5. Check System Resources"
echo "=========================================="
echo "CPU usage:"
top -bn1 | head -3

echo ""
echo "Memory usage:"
free -h

echo ""
echo "Disk I/O:"
iostat -x 1 2 2>/dev/null | tail -10

echo ""
echo "6. Test RADIUS Response Time"
echo "=========================================="
echo "Testing single RADIUS request..."
time radclient -c 1 127.0.0.1:1812 auth testing123 <<< "User-Name = aa:bb:cc:dd:ee:ff" 2>/dev/null

echo ""
echo "7. Check Network"
echo "=========================================="
echo "Listening ports:"
netstat -tlnp 2>/dev/null | grep -E "1812|5000" || ss -tlnp 2>/dev/null | grep -E "1812|5000"

echo ""
echo "8. Check Logs"
echo "=========================================="
echo "Recent FreeRADIUS errors:"
tail -20 /var/log/freeradius/radius.log 2>/dev/null | grep -i error || echo "No recent errors"

echo ""
echo "Recent FNAC errors:"
journalctl -u radius-server -n 20 2>/dev/null | grep -i error || echo "No recent errors"

echo ""
echo "=========================================="
echo "Diagnostics Complete"
echo "=========================================="
