# RADIUS Server Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         RADIUS Server System                             │
└─────────────────────────────────────────────────────────────────────────┘

                    ┌──────────────────────────────┐
                    │   Network Devices (Switches) │
                    │   Send RADIUS Requests       │
                    │   UDP Port 1812              │
                    └──────────────┬───────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │   RADIUS_Server              │
                    │   (RFC 2865 Handler)         │
                    │   - Verify device           │
                    │   - Extract MAC address     │
                    │   - Evaluate policy         │
                    │   - Generate response       │
                    └──────────────┬───────────────┘
                                   │
                ┌──────────────────┼──────────────────┐
                │                  │                  │
                ▼                  ▼                  ▼
        ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
        │   Device_    │  │   Client_    │  │   Policy_    │
        │   Manager    │  │   Manager    │  │   Engine     │
        │              │  │              │  │              │
        │ - Devices    │  │ - Clients    │  │ - Policies   │
        │ - Groups     │  │ - Groups     │  │ - Decisions  │
        │ - Verify IP  │  │ - MAC lookup │  │ - VLAN assign│
        └──────────────┘  └──────────────┘  └──────────────┘
                │                  │                  │
                └──────────────────┼──────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │   Log_Manager        │
                        │                      │
                        │ - Log events         │
                        │ - Filter logs        │
                        │ - Visual indicators  │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  Persistence Layer   │
                        │  (JSON Files)        │
                        │                      │
                        │ - devices.json       │
                        │ - clients.json       │
                        │ - policies.json      │
                        │ - logs.json          │
                        └──────────────────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  /etc/radius-server/ │
                        │  (Persistent Storage)│
                        └──────────────────────┘

                    ┌──────────────────────────────┐
                    │   Web Interface              │
                    │   HTTP Port 5000             │
                    │                              │
                    │ - Device Management          │
                    │ - Client Management          │
                    │ - Policy Management          │
                    │ - Log Viewer                 │
                    │ - REST API                   │
                    └──────────────────────────────┘
```

## Component Interaction Flow

### Authentication Request Flow

```
1. Network Device sends RADIUS Access-Request
   ↓
2. RADIUS_Server receives UDP packet on port 1812
   ↓
3. Device_Manager verifies device by IP and shared secret
   ├─ If not registered → Send Access-Reject
   └─ If registered → Continue
   ↓
4. Extract client MAC address from User-Name attribute
   ↓
5. Client_Manager looks up client by MAC address
   ├─ If not found → Send Access-Reject
   └─ If found → Get Client_Group
   ↓
6. Policy_Engine evaluates policy for Client_Group
   ├─ If ACCEPT_WITH_VLAN → Include VLAN in response
   ├─ If ACCEPT_WITHOUT_VLAN → Send Accept without VLAN
   └─ If REJECT or no policy → Send Access-Reject
   ↓
7. Log_Manager records authentication event
   ├─ Timestamp
   ├─ Client MAC
   ├─ Device ID
   ├─ Outcome (SUCCESS/FAILURE)
   └─ VLAN ID (if applicable)
   ↓
8. RADIUS_Server sends response to device
   ↓
9. Network device applies VLAN assignment (if applicable)
```

## Data Model Relationships

```
┌─────────────────────────────────────────────────────────────┐
│                    Device Management                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Device_Group (1)  ←──────→  (Many) Device                  │
│  ┌──────────────┐            ┌──────────────┐               │
│  │ id           │            │ id           │               │
│  │ name         │            │ ip_address   │               │
│  │ created_at   │            │ shared_secret│               │
│  │ updated_at   │            │ device_group │               │
│  └──────────────┘            │ created_at   │               │
│                              │ updated_at   │               │
│                              └──────────────┘               │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Client Management                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Client_Group (1)  ←──────→  (Many) Client                  │
│  ┌──────────────┐            ┌──────────────┐               │
│  │ id           │            │ mac_address  │               │
│  │ name         │            │ client_group │               │
│  │ created_at   │            │ created_at   │               │
│  │ updated_at   │            │ updated_at   │               │
│  └──────────────┘            └──────────────┘               │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Policy Management                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Client_Group (1)  ←──────→  (1) MAB_Policy                 │
│  ┌──────────────┐            ┌──────────────┐               │
│  │ id           │            │ id           │               │
│  │ name         │            │ client_group │               │
│  └──────────────┘            │ decision     │               │
│                              │ vlan_id      │               │
│                              │ created_at   │               │
│                              │ updated_at   │               │
│                              └──────────────┘               │
│                                                               │
│  PolicyDecision Enum:                                        │
│  - ACCEPT_WITH_VLAN                                          │
│  - ACCEPT_WITHOUT_VLAN                                       │
│  - REJECT                                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Authentication Logging                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Authentication_Log                                          │
│  ┌──────────────────────┐                                    │
│  │ id                   │                                    │
│  │ timestamp            │                                    │
│  │ client_mac           │                                    │
│  │ device_id            │                                    │
│  │ outcome              │ (SUCCESS or FAILURE)               │
│  │ vlan_id              │ (optional)                         │
│  │ created_at           │                                    │
│  └──────────────────────┘                                    │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## API Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Flask Web Application                     │
│                    (HTTP Port 5000)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              REST API Endpoints                       │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  Device Management:                                  │   │
│  │  ├─ GET    /api/devices                              │   │
│  │  ├─ POST   /api/devices                              │   │
│  │  ├─ PUT    /api/devices/{id}                         │   │
│  │  ├─ DELETE /api/devices/{id}                         │   │
│  │  ├─ GET    /api/device-groups                        │   │
│  │  ├─ POST   /api/device-groups                        │   │
│  │  └─ DELETE /api/device-groups/{id}                   │   │
│  │                                                        │   │
│  │  Client Management:                                  │   │
│  │  ├─ GET    /api/clients                              │   │
│  │  ├─ POST   /api/clients                              │   │
│  │  ├─ PUT    /api/clients/{mac}                        │   │
│  │  ├─ DELETE /api/clients/{mac}                        │   │
│  │  ├─ GET    /api/client-groups                        │   │
│  │  ├─ POST   /api/client-groups                        │   │
│  │  └─ DELETE /api/client-groups/{id}                   │   │
│  │                                                        │   │
│  │  Policy Management:                                  │   │
│  │  ├─ GET    /api/policies                             │   │
│  │  ├─ POST   /api/policies                             │   │
│  │  ├─ PUT    /api/policies/{id}                        │   │
│  │  └─ DELETE /api/policies/{id}                        │   │
│  │                                                        │   │
│  │  Log Viewing:                                        │   │
│  │  └─ GET    /api/logs (with optional filters)         │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Error Handling & Validation                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ✓ Input validation                                  │   │
│  │  ✓ Duplicate detection                              │   │
│  │  ✓ Referential integrity checks                     │   │
│  │  ✓ Descriptive error messages                       │   │
│  │  ✓ HTTP status codes                                │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Web UI (HTML/CSS/JavaScript)                 │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │                                                        │   │
│  │  ✓ Device management interface                       │   │
│  │  ✓ Client management interface                       │   │
│  │  ✓ Policy management interface                       │   │
│  │  ✓ Log viewer with filtering                         │   │
│  │  ✓ Visual indicators (green/red)                     │   │
│  │  ✓ Real-time updates                                 │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## RADIUS Protocol Implementation

```
┌─────────────────────────────────────────────────────────────┐
│              RADIUS Protocol Handler                         │
│              (RFC 2865 Compliant)                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Incoming RADIUS Packet (UDP 1812)                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  20-byte Header:                                     │   │
│  │  ├─ Code (1 byte): Access-Request (1)               │   │
│  │  ├─ ID (1 byte): Packet identifier                  │   │
│  │  ├─ Length (2 bytes): Total packet length           │   │
│  │  └─ Authenticator (16 bytes): MD5 hash              │   │
│  │                                                        │   │
│  │  Attributes (variable length):                       │   │
│  │  ├─ User-Name (1): Client MAC address               │   │
│  │  ├─ User-Password (2): Encrypted password           │   │
│  │  └─ Other attributes...                              │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Packet Validation:                                  │   │
│  │  ├─ Verify MD5 signature                             │   │
│  │  ├─ Check packet length                              │   │
│  │  ├─ Validate attributes                              │   │
│  │  └─ Verify device shared secret                      │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Response Generation:                                │   │
│  │                                                        │   │
│  │  Access-Accept (Code 2):                             │   │
│  │  ├─ Tunnel-Type (64): VLAN (13)                      │   │
│  │  ├─ Tunnel-Medium-Type (65): 802 (6)                │   │
│  │  └─ Tunnel-Private-Group-ID (81): VLAN ID           │   │
│  │                                                        │   │
│  │  Access-Reject (Code 3):                             │   │
│  │  └─ No attributes                                    │   │
│  │                                                        │   │
│  │  Response Authenticator:                             │   │
│  │  └─ MD5(Code + ID + Length + RequestAuth + Attrs)   │   │
│  │                                                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                           │                                   │
│                           ▼                                   │
│  Outgoing RADIUS Packet (UDP 1812)                          │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Data Persistence Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Persistence Layer                               │
│              (JSON-based, Atomic Writes)                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Write Operation:                                            │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Update in-memory data structure                  │   │
│  │  2. Serialize to JSON                                │   │
│  │  3. Write to temporary file                          │   │
│  │  4. Atomic rename (temp → final)                     │   │
│  │  5. Return success/failure                           │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Read Operation:                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Read JSON file                                   │   │
│  │  2. Parse JSON                                       │   │
│  │  3. Validate data integrity                          │   │
│  │  4. Load into in-memory data structures              │   │
│  │  5. Return data or error                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                               │
│  Storage Location: /etc/radius-server/                       │
│  ├─ devices.json                                             │
│  ├─ clients.json                                             │
│  ├─ policies.json                                            │
│  └─ logs.json                                                │
│                                                               │
│  Atomic Write Benefits:                                      │
│  ├─ No corruption on unexpected shutdown                     │
│  ├─ Consistent state always maintained                       │
│  ├─ Safe concurrent access                                   │
│  └─ Easy backup and recovery                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Testing Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Test Suite                                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Unit Tests (pytest):                                        │
│  ├─ test_device_manager.py                                  │
│  ├─ test_client_manager.py                                  │
│  ├─ test_policy_engine.py                                   │
│  ├─ test_log_manager.py                                     │
│  ├─ test_persistence.py                                     │
│  ├─ test_radius_server.py                                   │
│  └─ test_api.py                                             │
│                                                               │
│  Property-Based Tests (hypothesis):                          │
│  ├─ Device management properties                            │
│  ├─ Client management properties                            │
│  ├─ Policy evaluation properties                            │
│  ├─ Log management properties                               │
│  ├─ Persistence round-trip properties                       │
│  ├─ RADIUS protocol properties                              │
│  └─ Configuration validation properties                     │
│                                                               │
│  Test Coverage:                                              │
│  ├─ 44 correctness properties                               │
│  ├─ Edge cases and error conditions                         │
│  ├─ Integration scenarios                                   │
│  └─ Data persistence validation                             │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Deployment Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Production Deployment                           │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Systemd Service:                                            │
│  ├─ Service file: /etc/systemd/system/radius-server.service │
│  ├─ User: radius (unprivileged)                             │
│  ├─ Auto-restart on failure                                 │
│  └─ Integrated logging                                      │
│                                                               │
│  File Permissions:                                           │
│  ├─ /etc/radius-server/: radius:radius (755)               │
│  ├─ Configuration files: radius:radius (644)                │
│  └─ Log files: radius:radius (644)                          │
│                                                               │
│  Monitoring:                                                 │
│  ├─ systemctl status radius-server                          │
│  ├─ journalctl -u radius-server -f                          │
│  └─ API health checks                                       │
│                                                               │
│  Backup Strategy:                                            │
│  ├─ Daily snapshots of /etc/radius-server/                  │
│  ├─ Version control for code                                │
│  └─ Log archival (30-day retention)                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Security Considerations

```
┌─────────────────────────────────────────────────────────────┐
│                    Security Features                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  RADIUS Protocol Security:                                   │
│  ├─ MD5-based message authentication                        │
│  ├─ Shared secret verification                              │
│  ├─ Device IP validation                                    │
│  └─ Packet integrity checks                                 │
│                                                               │
│  Data Protection:                                            │
│  ├─ Atomic file writes (no corruption)                      │
│  ├─ File permissions (600 for sensitive data)               │
│  ├─ Validation on load                                      │
│  └─ Referential integrity enforcement                       │
│                                                               │
│  API Security:                                               │
│  ├─ Input validation on all endpoints                       │
│  ├─ Error message sanitization                              │
│  ├─ Rate limiting (recommended)                             │
│  └─ HTTPS support (recommended for production)              │
│                                                               │
│  Operational Security:                                       │
│  ├─ Run as unprivileged user (radius)                       │
│  ├─ Minimal file permissions                                │
│  ├─ Audit logging of all events                             │
│  └─ Regular backups                                         │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

This architecture provides a modular, scalable, and maintainable RADIUS server implementation suitable for network access control in enterprise environments.
