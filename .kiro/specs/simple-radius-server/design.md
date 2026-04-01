# Design Document: Simple RADIUS Server

## Overview

The Simple RADIUS Server is a network access control system that implements MAC Authentication Bypass (MAB) for network devices. It manages network devices, authenticates clients based on MAC addresses, applies policy-based VLAN assignments, and maintains audit logs of authentication events. The system is designed to run on Debian-based operating systems and implements the standard RADIUS protocol (RFC 2865) on UDP port 1812.

### Key Design Goals

- **Modularity**: Clear separation of concerns with distinct components for device management, client management, policy evaluation, and logging
- **Compliance**: Full RFC 2865 RADIUS protocol compliance
- **Persistence**: All configuration and logs survive server restarts
- **Auditability**: Complete audit trail of authentication events with visual indicators
- **Extensibility**: Component-based architecture allows future enhancements

## Architecture

### System Components

The system is organized into five core components that interact through well-defined interfaces:

```
┌─────────────────────────────────────────────────────────────┐
│                    RADIUS_Server                             │
│  (UDP 1812 listener, RFC 2865 protocol handler)             │
└────────────────┬────────────────────────────────────────────┘
                 │
    ┌────────────┼────────────┬──────────────┬──────────────┐
    │            │            │              │              │
    ▼            ▼            ▼              ▼              ▼
┌─────────┐ ┌─────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐
│ Device_ │ │ Client_ │ │ Policy_  │ │   Log_   │ │Persistence
│Manager  │ │Manager  │ │ Engine   │ │ Manager  │ │ Layer
└─────────┘ └─────────┘ └──────────┘ └──────────┘ └──────────┘
```

### Component Responsibilities

**RADIUS_Server**
- Listens on UDP port 1812 for incoming RADIUS authentication requests
- Validates requests originate from registered devices
- Extracts client MAC addresses from requests
- Orchestrates authentication flow by coordinating with other components
- Constructs and sends RADIUS responses (Access-Accept, Access-Reject)
- Delegates logging to Log_Manager

**Device_Manager**
- Manages Device entities (unique identifier, IP address, shared secret)
- Manages Device_Group entities
- Enforces one-to-one relationship between Device and Device_Group
- Maintains referential integrity when devices or groups are removed
- Provides device lookup by identifier and IP address
- Persists device data

**Client_Manager**
- Manages Client entities (MAC address as unique identifier)
- Manages Client_Group entities
- Validates MAC address format (XX:XX:XX:XX:XX:XX)
- Enforces one-to-one relationship between Client and Client_Group
- Maintains referential integrity when clients or groups are removed
- Provides client lookup by MAC address
- Persists client data

**Policy_Engine**
- Manages MAB_Policy entities that map Client_Group to authentication decisions
- Supports three policy types: Accept with VLAN, Accept without VLAN, Reject
- Evaluates policies to determine authentication response
- Handles missing policies (default: Reject)
- Persists policy data

**Log_Manager**
- Records Authentication_Log entries for all authentication attempts
- Captures timestamp, client MAC, device identifier, outcome, and optional VLAN_ID
- Provides log viewing with reverse chronological ordering
- Supports filtering by date range, MAC address, and outcome
- Provides visual indicators (green for success, red for failure)
- Persists log data

## Components and Interfaces

### Device_Manager Interface

```
class Device:
  - id: string (unique identifier)
  - ip_address: string (IPv4 address)
  - shared_secret: string (RADIUS shared secret)
  - device_group_id: string (foreign key to Device_Group)

class Device_Group:
  - id: string (unique identifier)
  - name: string

interface Device_Manager:
  + create_device(id, ip_address, shared_secret, device_group_id) -> Device
  + update_device(id, ip_address, shared_secret, device_group_id) -> Device
  + delete_device(id) -> void
  + get_device(id) -> Device | null
  + get_device_by_ip(ip_address) -> Device | null
  + list_devices() -> List[Device]
  + create_device_group(id, name) -> Device_Group
  + delete_device_group(id) -> void
  + get_device_group(id) -> Device_Group | null
  + list_device_groups() -> List[Device_Group]
```

### Client_Manager Interface

```
class Client:
  - mac_address: string (unique identifier, format: XX:XX:XX:XX:XX:XX)
  - client_group_id: string (foreign key to Client_Group)

class Client_Group:
  - id: string (unique identifier)
  - name: string

interface Client_Manager:
  + create_client(mac_address, client_group_id) -> Client
  + update_client(mac_address, client_group_id) -> Client
  + delete_client(mac_address) -> void
  + get_client(mac_address) -> Client | null
  + list_clients() -> List[Client]
  + validate_mac_address(mac_address) -> bool
  + create_client_group(id, name) -> Client_Group
  + delete_client_group(id) -> void
  + get_client_group(id) -> Client_Group | null
  + list_client_groups() -> List[Client_Group]
```

### Policy_Engine Interface

```
enum PolicyDecision:
  - ACCEPT_WITH_VLAN
  - ACCEPT_WITHOUT_VLAN
  - REJECT

class MAB_Policy:
  - id: string (unique identifier)
  - client_group_id: string (foreign key to Client_Group)
  - decision: PolicyDecision
  - vlan_id: int | null (only set if decision is ACCEPT_WITH_VLAN)

interface Policy_Engine:
  + create_policy(client_group_id, decision, vlan_id) -> MAB_Policy
  + update_policy(id, decision, vlan_id) -> MAB_Policy
  + delete_policy(id) -> void
  + get_policy(id) -> MAB_Policy | null
  + get_policy_by_client_group(client_group_id) -> MAB_Policy | null
  + list_policies() -> List[MAB_Policy]
  + evaluate_policy(client_group_id) -> PolicyDecision, vlan_id | null
```

### Log_Manager Interface

```
enum AuthenticationOutcome:
  - SUCCESS
  - FAILURE

class Authentication_Log:
  - id: string (unique identifier)
  - timestamp: datetime
  - client_mac: string
  - device_id: string
  - outcome: AuthenticationOutcome
  - vlan_id: int | null

interface Log_Manager:
  + create_log_entry(client_mac, device_id, outcome, vlan_id) -> Authentication_Log
  + list_logs() -> List[Authentication_Log]  // reverse chronological order
  + filter_logs(date_start, date_end, mac_address, outcome) -> List[Authentication_Log]
  + get_log_entry(id) -> Authentication_Log | null
```

## Data Models

### Device Data Model

```
Device {
  id: string (unique, e.g., "switch-01")
  ip_address: string (IPv4 format)
  shared_secret: string (RADIUS shared secret, min 16 chars recommended)
  device_group_id: string (foreign key)
  created_at: timestamp
  updated_at: timestamp
}

Device_Group {
  id: string (unique, e.g., "access-layer")
  name: string
  created_at: timestamp
  updated_at: timestamp
}
```

### Client Data Model

```
Client {
  mac_address: string (unique, format: XX:XX:XX:XX:XX:XX)
  client_group_id: string (foreign key)
  created_at: timestamp
  updated_at: timestamp
}

Client_Group {
  id: string (unique, e.g., "printers")
  name: string
  created_at: timestamp
  updated_at: timestamp
}
```

### Policy Data Model

```
MAB_Policy {
  id: string (unique)
  client_group_id: string (foreign key, unique constraint)
  decision: enum (ACCEPT_WITH_VLAN | ACCEPT_WITHOUT_VLAN | REJECT)
  vlan_id: int | null (only populated if decision is ACCEPT_WITH_VLAN)
  created_at: timestamp
  updated_at: timestamp
}
```

### Authentication Log Data Model

```
Authentication_Log {
  id: string (unique)
  timestamp: datetime (ISO 8601 format)
  client_mac: string
  device_id: string
  outcome: enum (SUCCESS | FAILURE)
  vlan_id: int | null
  created_at: timestamp
}
```

## RADIUS Protocol Handling

### RFC 2865 Compliance

The system implements RFC 2865 RADIUS protocol with the following characteristics:

- **Transport**: UDP on port 1812 (standard RADIUS authentication port)
- **Message Format**: RADIUS packet structure with 20-byte header and variable-length attributes
- **Authentication**: Shared secret-based message authentication using MD5
- **Request Types**: Access-Request (code 1)
- **Response Types**: Access-Accept (code 2), Access-Reject (code 3)

### Authentication Flow

```
1. Device sends RADIUS Access-Request (UDP 1812)
   - Contains: User-Name (MAC address), User-Password (MAC address)
   - Signed with device's shared secret

2. RADIUS_Server receives request
   - Validates request signature using device's shared secret
   - Verifies device is registered
   - Extracts User-Name (client MAC address)

3. RADIUS_Server queries Client_Manager
   - Looks up client by MAC address
   - Retrieves associated Client_Group

4. RADIUS_Server queries Policy_Engine
   - Evaluates policy for Client_Group
   - Determines response type and VLAN assignment

5. RADIUS_Server constructs response
   - Access-Accept: includes VLAN attribute if applicable
   - Access-Reject: no attributes
   - Signs response with device's shared secret

6. RADIUS_Server sends response to device

7. Log_Manager records authentication event
   - Captures all relevant details
   - Marks as success or failure
```

### RADIUS Attributes Used

- **User-Name** (1): Client MAC address
- **User-Password** (2): Client MAC address (encrypted with shared secret)
- **Tunnel-Type** (64): VLAN (value 13)
- **Tunnel-Medium-Type** (65): 802 (value 6)
- **Tunnel-Private-Group-ID** (81): VLAN ID (when applicable)

## Configuration Interface Design

### Configuration Interface Components

The configuration interface provides four main sections:

1. **Device Management**
   - Add/edit/delete devices
   - Assign devices to groups
   - View all devices and their groups

2. **Client Management**
   - Add/edit/delete clients (MAC addresses)
   - Assign clients to groups
   - Validate MAC address format
   - View all clients and their groups

3. **Policy Management**
   - Create/edit/delete policies
   - Map client groups to authentication decisions
   - Configure VLAN assignments
   - View all policies

4. **Log Viewer**
   - Display authentication logs in reverse chronological order
   - Filter by date range, MAC address, outcome
   - Visual indicators (green/red) for success/failure
   - Export logs (optional)

### Error Handling in Configuration

- Invalid MAC address format: "Invalid MAC address format. Expected XX:XX:XX:XX:XX:XX"
- Duplicate device ID: "Device ID already exists"
- Duplicate client MAC: "Client MAC address already exists"
- Missing required fields: "Field [name] is required"
- Invalid VLAN ID: "VLAN ID must be between 1 and 4094"
- Referential integrity violations: "Cannot delete group with assigned devices/clients"

## Data Persistence Strategy

### Persistence Layer

The system uses a file-based persistence layer with the following characteristics:

- **Format**: JSON for human readability and ease of debugging
- **Location**: `/etc/radius-server/` (configurable)
- **Files**:
  - `devices.json`: Device and Device_Group data
  - `clients.json`: Client and Client_Group data
  - `policies.json`: MAB_Policy data
  - `logs.json`: Authentication_Log entries

### Persistence Operations

**On Startup**:
1. Load all JSON files in order: devices, clients, policies, logs
2. Validate data integrity
3. Initialize in-memory data structures
4. Begin accepting RADIUS requests

**On Data Change**:
1. Update in-memory data structure
2. Write updated JSON file atomically (write to temp file, then rename)
3. Return success/failure to caller

**Log Rotation** (optional):
- Archive logs older than 30 days to `logs-archive/`
- Maintain current logs in `logs.json`

### Data Integrity

- Atomic writes prevent corruption on unexpected shutdown
- Referential integrity constraints enforced in-memory
- Validation on load detects corrupted data
- Backup strategy: daily snapshots of configuration files

## Integration Points Between Components

### RADIUS_Server ↔ Device_Manager

```
RADIUS_Server.handle_request(packet):
  device = Device_Manager.get_device_by_ip(packet.source_ip)
  if device is null:
    return Access_Reject
  if not verify_signature(packet, device.shared_secret):
    return Access_Reject
```

### RADIUS_Server ↔ Client_Manager

```
RADIUS_Server.handle_request(packet):
  mac_address = extract_mac_from_packet(packet)
  client = Client_Manager.get_client(mac_address)
  if client is null:
    Log_Manager.create_log_entry(mac_address, device.id, FAILURE, null)
    return Access_Reject
```

### RADIUS_Server ↔ Policy_Engine

```
RADIUS_Server.handle_request(packet):
  decision, vlan_id = Policy_Engine.evaluate_policy(client.client_group_id)
  if decision == ACCEPT_WITH_VLAN:
    response = create_accept_response(vlan_id)
    Log_Manager.create_log_entry(mac_address, device.id, SUCCESS, vlan_id)
  elif decision == ACCEPT_WITHOUT_VLAN:
    response = create_accept_response(null)
    Log_Manager.create_log_entry(mac_address, device.id, SUCCESS, null)
  else:  # REJECT
    response = create_reject_response()
    Log_Manager.create_log_entry(mac_address, device.id, FAILURE, null)
```

### Configuration Interface ↔ All Managers

```
ConfigInterface.add_device(id, ip, secret, group_id):
  try:
    device = Device_Manager.create_device(id, ip, secret, group_id)
    return success_response(device)
  catch ValidationError as e:
    return error_response(e.message)
```

### Persistence Layer ↔ All Managers

```
Device_Manager.create_device(...):
  device = Device(...)
  devices_list.append(device)
  Persistence.write_devices(devices_list)
  return device
```

## Error Handling

### Device Management Errors

- Device ID already exists → Return error, don't create
- Device Group not found → Return error, don't create device
- Invalid IP address format → Return error
- Shared secret too short → Return error (recommend 16+ chars)
- Cannot delete group with assigned devices → Return error

### Client Management Errors

- Invalid MAC address format → Return error
- MAC address already exists → Return error
- Client Group not found → Return error
- Cannot delete group with assigned clients → Return error

### Policy Management Errors

- Client Group not found → Return error
- Invalid VLAN ID (not 1-4094) → Return error
- Policy already exists for group → Return error (update instead)

### RADIUS Protocol Errors

- Request from unregistered device → Send Access-Reject
- Invalid request signature → Send Access-Reject
- Client MAC not found → Send Access-Reject
- No policy for client group → Send Access-Reject
- Malformed RADIUS packet → Silently drop (per RFC 2865)

### Persistence Errors

- Cannot read configuration file → Log error, use empty state
- Cannot write configuration file → Log error, return failure to user
- Corrupted JSON data → Log error, attempt recovery or use backup

## Testing Strategy

### Unit Testing Approach

Unit tests verify specific examples, edge cases, and error conditions:

- Device creation with valid/invalid inputs
- MAC address validation (valid formats, edge cases)
- Policy evaluation with different decision types
- Log filtering by various criteria
- Error message generation
- Referential integrity violations
- Persistence read/write operations

### Property-Based Testing Approach

Property-based tests verify universal properties across all inputs:

- Device management maintains one-to-one group assignment
- Client management maintains one-to-one group assignment
- Policy evaluation is deterministic
- Log entries contain all required fields
- Persistence round-trip (write then read returns same data)
- RADIUS protocol compliance
- Configuration validation rejects invalid inputs

### Test Configuration

- Minimum 100 iterations per property test
- Each property test tagged with design reference
- Tag format: `Feature: simple-radius-server, Property {number}: {property_text}`
- Both unit and property tests required for comprehensive coverage



## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Device Creation Preserves Attributes

*For any* device creation with valid inputs (unique ID, valid IP address, shared secret, valid group ID), the created device SHALL have all attributes exactly as specified.

**Validates: Requirements 1.1**

### Property 2: Device-Group Assignment is One-to-One

*For any* device in the system, the device SHALL be assigned to exactly one Device_Group, and this assignment SHALL be immutable until explicitly updated.

**Validates: Requirements 1.2**

### Property 3: Device Update Applies Changes

*For any* device and any valid update to its attributes (IP address, shared secret, group assignment), the device SHALL reflect the updated values after the update operation completes.

**Validates: Requirements 1.3**

### Property 4: Device Removal is Complete

*For any* device in the system, after deletion, the device SHALL no longer appear in any device listing or lookup operation.

**Validates: Requirements 1.4**

### Property 5: Device Group Lifecycle

*For any* Device_Group creation and deletion, the group SHALL exist in the system after creation and SHALL not exist after deletion.

**Validates: Requirements 1.5**

### Property 6: Device Removal Maintains Referential Integrity

*For any* device removal, the system state SHALL remain consistent—no orphaned references, no broken relationships, and all remaining devices SHALL maintain valid group assignments.

**Validates: Requirements 1.6**

### Property 7: Device Listing is Complete and Accurate

*For any* set of devices created in the system, the device listing operation SHALL return all devices with their correct group assignments, and no additional devices.

**Validates: Requirements 1.7**

### Property 8: Client Creation with MAC Address

*For any* client creation with a valid MAC address and group ID, the created client SHALL have the MAC address as its unique identifier and the specified group assignment.

**Validates: Requirements 2.1**

### Property 9: Client-Group Assignment is One-to-One

*For any* client in the system, the client SHALL be assigned to exactly one Client_Group, and this assignment SHALL be immutable until explicitly updated.

**Validates: Requirements 2.2**

### Property 10: MAC Address Validation

*For any* string input, if the string matches the format XX:XX:XX:XX:XX:XX (where X is a hexadecimal digit), the MAC address validation SHALL succeed; otherwise, it SHALL fail.

**Validates: Requirements 2.3**

### Property 11: Client Update Applies Changes

*For any* client and any valid update to its group assignment, the client SHALL reflect the updated group after the update operation completes.

**Validates: Requirements 2.4**

### Property 12: Client Removal is Complete

*For any* client in the system, after deletion, the client SHALL no longer appear in any client listing or lookup operation.

**Validates: Requirements 2.5**

### Property 13: Client Group Lifecycle

*For any* Client_Group creation and deletion, the group SHALL exist in the system after creation and SHALL not exist after deletion.

**Validates: Requirements 2.6**

### Property 14: Client Removal Maintains Referential Integrity

*For any* client removal, the system state SHALL remain consistent—no orphaned references, no broken relationships, and all remaining clients SHALL maintain valid group assignments.

**Validates: Requirements 2.7**

### Property 15: Client Listing is Complete and Accurate

*For any* set of clients created in the system, the client listing operation SHALL return all clients with their correct group assignments, and no additional clients.

**Validates: Requirements 2.8**

### Property 16: Policy Creation Maps Client Group to Decision

*For any* policy creation with a valid client group ID and decision type, the created policy SHALL map the client group to the specified decision.

**Validates: Requirements 3.1**

### Property 17: Policy Accept with VLAN Configuration

*For any* policy configured with decision ACCEPT_WITH_VLAN and a valid VLAN ID, the policy SHALL store the VLAN ID and return it during evaluation.

**Validates: Requirements 3.2**

### Property 18: Policy Accept without VLAN Configuration

*For any* policy configured with decision ACCEPT_WITHOUT_VLAN, the policy SHALL not store a VLAN ID and SHALL return null for VLAN during evaluation.

**Validates: Requirements 3.3**

### Property 19: Policy Reject Configuration

*For any* policy configured with decision REJECT, the policy SHALL return REJECT during evaluation regardless of other parameters.

**Validates: Requirements 3.4**

### Property 20: Policy Update Applies Changes

*For any* policy and any valid update to its decision or VLAN ID, the policy SHALL reflect the updated values after the update operation completes.

**Validates: Requirements 3.5**

### Property 21: Policy Removal is Complete

*For any* policy in the system, after deletion, the policy SHALL no longer appear in any policy listing or lookup operation.

**Validates: Requirements 3.6**

### Property 22: Policy Listing is Complete and Accurate

*For any* set of policies created in the system, the policy listing operation SHALL return all policies with their associated client groups and response behaviors, and no additional policies.

**Validates: Requirements 3.7**

### Property 23: RADIUS Request Device Verification

*For any* RADIUS authentication request, if the request originates from a registered device (verified by IP address and shared secret), the request SHALL proceed to MAC extraction; if from an unregistered device, the request SHALL be rejected.

**Validates: Requirements 4.1, 4.2**

### Property 24: MAC Address Extraction from RADIUS Request

*For any* valid RADIUS request from a registered device, the system SHALL successfully extract the client MAC address from the User-Name attribute.

**Validates: Requirements 4.3**

### Property 25: Client Group Lookup

*For any* client MAC address found in the Client_Manager, the system SHALL retrieve the associated Client_Group without error.

**Validates: Requirements 4.4**

### Property 26: Unknown Client Rejection

*For any* RADIUS request with a client MAC address not found in the Client_Manager, the system SHALL return Access_Reject.

**Validates: Requirements 4.5**

### Property 27: Policy Application

*For any* client group with an associated MAB_Policy, the system SHALL apply the policy to generate the authentication response.

**Validates: Requirements 4.6**

### Property 28: Accept with VLAN Response

*For any* MAB_Policy with decision ACCEPT_WITH_VLAN and a specified VLAN ID, the RADIUS Access_Accept response SHALL include the VLAN ID in the Tunnel-Private-Group-ID attribute.

**Validates: Requirements 4.7**

### Property 29: Accept without VLAN Response

*For any* MAB_Policy with decision ACCEPT_WITHOUT_VLAN, the RADIUS Access_Accept response SHALL not include any VLAN attributes.

**Validates: Requirements 4.8**

### Property 30: Reject Response

*For any* MAB_Policy with decision REJECT, the system SHALL return RADIUS Access_Reject.

**Validates: Requirements 4.9**

### Property 31: Missing Policy Default Rejection

*For any* client group without an associated MAB_Policy, the system SHALL return Access_Reject.

**Validates: Requirements 4.10**

### Property 32: Successful Authentication Logging

*For any* RADIUS Access_Accept response sent by the system, the Log_Manager SHALL create an Authentication_Log entry marked as SUCCESS.

**Validates: Requirements 5.1**

### Property 33: Failed Authentication Logging

*For any* RADIUS Access_Reject response sent by the system, the Log_Manager SHALL create an Authentication_Log entry marked as FAILURE.

**Validates: Requirements 5.2**

### Property 34: Log Entry Completeness

*For any* Authentication_Log entry created, the entry SHALL contain timestamp, client MAC address, device identifier, and authentication outcome.

**Validates: Requirements 5.3**

### Property 35: VLAN Logging

*For any* authentication response that includes a VLAN ID assignment, the Authentication_Log entry SHALL include the VLAN ID.

**Validates: Requirements 5.4**

### Property 36: Log Ordering

*For any* set of authentication logs, the listing operation SHALL return logs in reverse chronological order (newest first).

**Validates: Requirements 5.7**

### Property 37: Log Filtering

*For any* filter criteria (date range, MAC address, outcome), the log filtering operation SHALL return only logs matching all specified criteria.

**Validates: Requirements 5.8**

### Property 38: RFC 2865 Protocol Compliance

*For any* RADIUS message sent by the system, the message SHALL conform to RFC 2865 format: 20-byte header, valid message type (Access-Accept or Access-Reject), correct attribute encoding, and valid message authentication code.

**Validates: Requirements 6.3**

### Property 39: Device Persistence Round-Trip

*For any* set of devices and device groups created in the system, after writing to persistent storage and reading back, the retrieved data SHALL be identical to the original data.

**Validates: Requirements 7.1**

### Property 40: Client Persistence Round-Trip

*For any* set of clients and client groups created in the system, after writing to persistent storage and reading back, the retrieved data SHALL be identical to the original data.

**Validates: Requirements 7.2**

### Property 41: Policy Persistence Round-Trip

*For any* set of MAB_Policies created in the system, after writing to persistent storage and reading back, the retrieved data SHALL be identical to the original data.

**Validates: Requirements 7.3**

### Property 42: Log Persistence Round-Trip

*For any* set of Authentication_Log entries created in the system, after writing to persistent storage and reading back, the retrieved data SHALL be identical to the original data.

**Validates: Requirements 7.4**

### Property 43: Data Loading on Startup

*For any* system startup, the system SHALL load all persisted data from storage before accepting any RADIUS authentication requests.

**Validates: Requirements 7.5**

### Property 44: Configuration Validation

*For any* invalid configuration data submitted through the interface (invalid MAC format, missing required fields, invalid VLAN ID, duplicate IDs), the system SHALL reject the submission and return a descriptive error message.

**Validates: Requirements 8.5, 8.6**

