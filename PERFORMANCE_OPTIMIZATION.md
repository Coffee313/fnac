# Performance Optimization for 1000+ req/s

## Current Architecture Analysis

### What Handles RADIUS Requests?
- **FreeRADIUS** (UDP port 1812) - Handles authentication requests
- **FNAC** (HTTP port 5000) - Management UI only, not for auth requests

### Current Bottlenecks

1. **Logging to SQLite** - Synchronous writes block on every auth
2. **JSON file persistence** - Atomic writes are slow for frequent updates
3. **Python Flask** - Single-threaded by default, not for high-throughput

## Performance Optimization Strategy

### 1. Async Logging (Critical)

Replace synchronous SQLite writes with async queue:

```python
# Use asyncio queue for logging
import asyncio
from collections import deque

class AsyncLogWriter:
    def __init__(self, batch_size=100, flush_interval=1.0):
        self.queue = asyncio.Queue()
        self.batch_size = batch_size
        self.flush_interval = flush_interval
    
    async def log_async(self, log_entry):
        """Non-blocking log write"""
        await self.queue.put(log_entry)
    
    async def batch_writer(self):
        """Batch writes to database"""
        batch = []
        while True:
            try:
                # Wait for batch or timeout
                log_entry = await asyncio.wait_for(
                    self.queue.get(), 
                    timeout=self.flush_interval
                )
                batch.append(log_entry)
                
                if len(batch) >= self.batch_size:
                    await self._flush_batch(batch)
                    batch = []
            except asyncio.TimeoutError:
                if batch:
                    await self._flush_batch(batch)
                    batch = []
    
    async def _flush_batch(self, batch):
        """Write batch to database"""
        # Bulk insert to SQLite
        pass
```

### 2. Use Redis for Logging (Recommended)

Replace SQLite with Redis for real-time logging:

```bash
# Install Redis
apt-get install redis-server

# Configure for high throughput
# /etc/redis/redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
appendonly no  # Disable persistence for speed
```

Benefits:
- In-memory, extremely fast
- Supports pub/sub for real-time updates
- Automatic expiration (TTL)
- Can persist to disk periodically

### 3. Connection Pooling

Use connection pooling for database access:

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    'sqlite:///fnac.db',
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True
)
```

### 4. Caching Layer

Cache frequently accessed data:

```python
from functools import lru_cache
import time

class CachedPolicyEngine:
    def __init__(self, ttl=60):
        self.cache = {}
        self.ttl = ttl
    
    def get_policy(self, client_group_name):
        """Get policy with caching"""
        cache_key = f"policy:{client_group_name}"
        
        if cache_key in self.cache:
            cached_data, timestamp = self.cache[cache_key]
            if time.time() - timestamp < self.ttl:
                return cached_data
        
        # Fetch from database
        policy = self._fetch_policy(client_group_name)
        self.cache[cache_key] = (policy, time.time())
        return policy
```

### 5. FreeRADIUS Tuning

Optimize FreeRADIUS configuration:

```
# /etc/freeradius/3.0/radiusd.conf

# Increase thread pool
thread pool {
    start_servers = 32
    max_servers = 256
    min_spare_servers = 8
    max_spare_servers = 32
    max_requests_per_server = 0
}

# Optimize network
listen {
    type = auth
    port = 1812
    ipaddr = *
    
    # Increase socket buffer
    recv_buff = 65536
    send_buff = 65536
}

# Disable unnecessary modules
modules {
    # Only load needed modules
    # Disable: ldap, sql, etc.
}
```

### 6. Database Optimization

For SQLite (if keeping it):

```python
# Optimize SQLite for writes
conn.execute("PRAGMA journal_mode=WAL")      # Write-Ahead Logging
conn.execute("PRAGMA synchronous=NORMAL")    # Faster writes
conn.execute("PRAGMA cache_size=10000")      # Larger cache
conn.execute("PRAGMA temp_store=MEMORY")     # Temp in RAM
conn.execute("PRAGMA mmap_size=30000000000") # Memory-mapped I/O
```

Or use PostgreSQL for better concurrency:

```python
# PostgreSQL is much better for high throughput
from sqlalchemy import create_engine

engine = create_engine(
    'postgresql://user:password@localhost/fnac',
    pool_size=20,
    max_overflow=40,
    echo=False
)
```

### 7. Batch Operations

Batch database operations:

```python
def save_logs_batch(logs):
    """Batch insert logs"""
    db = Database()
    conn = db.get_connection()
    cursor = conn.cursor()
    
    # Single transaction for multiple inserts
    cursor.executemany("""
        INSERT INTO auth_logs 
        (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_name)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, [(l.id, l.timestamp, l.client_mac, l.device_id, 
           l.outcome.value, l.vlan_id, l.policy_name) for l in logs])
    
    conn.commit()
    conn.close()
```

## Implementation Roadmap

### Phase 1: Immediate (1-2 hours)
- [ ] Enable SQLite WAL mode
- [ ] Implement async logging queue
- [ ] Add connection pooling
- [ ] Batch log writes (100 logs per batch)

### Phase 2: Short-term (1 day)
- [ ] Add Redis for logging
- [ ] Implement caching layer
- [ ] Optimize FreeRADIUS config
- [ ] Load testing

### Phase 3: Long-term (1 week)
- [ ] Migrate to PostgreSQL
- [ ] Add monitoring/metrics
- [ ] Implement rate limiting
- [ ] Add horizontal scaling

## Expected Performance Improvements

| Optimization | Impact | Effort |
|---|---|---|
| SQLite WAL + PRAGMA tuning | 2-3x | Low |
| Async logging queue | 5-10x | Medium |
| Redis logging | 10-50x | Medium |
| Connection pooling | 2-3x | Low |
| Batch operations | 3-5x | Low |
| PostgreSQL | 5-10x | High |
| **Combined** | **50-100x** | **High** |

## Testing Performance

```bash
# Load test with Apache Bench
ab -n 10000 -c 100 http://localhost:5000/api/logs

# Load test RADIUS with radclient
for i in {1..1000}; do
    echo "User-Name = aa:bb:cc:dd:ee:ff" | \
    radclient -c 1 192.168.1.1:1812 auth testing123 &
done
wait
```

## Monitoring

```bash
# Monitor FreeRADIUS
radwho

# Monitor database
sqlite3 fnac.db "SELECT COUNT(*) FROM auth_logs;"

# Monitor system
top -p $(pgrep -f radiusd)
```

## Recommendations

1. **For 1000 req/s**: Use Redis + async logging + FreeRADIUS tuning
2. **For 10,000 req/s**: Add PostgreSQL + horizontal scaling
3. **For 100,000+ req/s**: Use dedicated RADIUS appliance or cloud service

The bottleneck is NOT FNAC (management UI), it's the logging layer. FreeRADIUS itself can handle 10,000+ req/s easily.
