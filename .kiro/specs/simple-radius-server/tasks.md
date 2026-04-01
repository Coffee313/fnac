# Implementation Plan: Simple RADIUS Server

## Overview

This implementation plan breaks down the Simple RADIUS Server feature into discrete, actionable coding tasks. The system will be built incrementally, starting with project infrastructure and data models, then implementing core components, the RADIUS protocol handler, configuration interface, and finally integration and testing. Each task builds on previous work with no orphaned code.

## Tasks

- [x] 1. Project setup and core infrastructure
  - Create project directory structure with `src/`, `tests/`, `config/` directories
  - Set up Python virtual environment and requirements.txt with dependencies (pyradius, flask, pytest, hypothesis)
  - Create main entry point script that initializes the server
  - Define core type hints and data classes for Device, Client, Policy, and Log entities
  - Set up logging configuration for the application
  - _Requirements: 6.1, 6.2, 7.5_

- [x] 2. Implement persistence layer
  - [x] 2.1 Create JSON-based persistence module
    - Implement atomic file write operations (write to temp file, then rename)
    - Create load/save functions for each data type (devices, clients, policies, logs)
    - Implement data validation on load to detect corruption
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 2.2 Write property test for persistence round-trip
    - **Property 39: Device Persistence Round-Trip**
    - **Validates: Requirements 7.1**
  
  - [x] 2.3 Write property test for client persistence round-trip
    - **Property 40: Client Persistence Round-Trip**
    - **Validates: Requirements 7.2**
  
  - [x] 2.4 Write property test for policy persistence round-trip
    - **Property 41: Policy Persistence Round-Trip**
    - **Validates: Requirements 7.3**
  
  - [x] 2.5 Write property test for log persistence round-trip
    - **Property 42: Log Persistence Round-Trip**
    - **Validates: Requirements 7.4**

- [x] 3. Implement Device_Manager component
  - [x] 3.1 Create Device and Device_Group data models
    - Define Device class with id, ip_address, shared_secret, device_group_id, created_at, updated_at
    - Define Device_Group class with id, name, created_at, updated_at
    - Implement validation for IP address format
    - _Requirements: 1.1, 1.2_
  
  - [x] 3.2 Write property test for device creation
    - **Property 1: Device Creation Preserves Attributes**
    - **Validates: Requirements 1.1**
  
  - [x] 3.3 Implement Device_Manager interface
    - Implement create_device, update_device, delete_device, get_device, get_device_by_ip, list_devices
    - Implement create_device_group, delete_device_group, get_device_group, list_device_groups
    - Enforce one-to-one Device-to-Device_Group relationship
    - Maintain referential integrity when deleting devices or groups
    - Persist changes to devices.json
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_
  
  - [x] 3.4 Write property tests for Device_Manager
    - **Property 2: Device-Group Assignment is One-to-One**
    - **Property 3: Device Update Applies Changes**
    - **Property 4: Device Removal is Complete**
    - **Property 5: Device Group Lifecycle**
    - **Property 6: Device Removal Maintains Referential Integrity**
    - **Property 7: Device Listing is Complete and Accurate**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7**

- [x] 4. Implement Client_Manager component
  - [x] 4.1 Create Client and Client_Group data models
    - Define Client class with mac_address, client_group_id, created_at, updated_at
    - Define Client_Group class with id, name, created_at, updated_at
    - Implement MAC address validation (XX:XX:XX:XX:XX:XX format)
    - _Requirements: 2.1, 2.3_
  
  - [x] 4.2 Write property test for MAC address validation
    - **Property 10: MAC Address Validation**
    - **Validates: Requirements 2.3**
  
  - [x] 4.3 Implement Client_Manager interface
    - Implement create_client, update_client, delete_client, get_client, list_clients
    - Implement create_client_group, delete_client_group, get_client_group, list_client_groups
    - Enforce one-to-one Client-to-Client_Group relationship
    - Maintain referential integrity when deleting clients or groups
    - Persist changes to clients.json
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_
  
  - [x] 4.4 Write property tests for Client_Manager
    - **Property 8: Client Creation with MAC Address**
    - **Property 9: Client-Group Assignment is One-to-One**
    - **Property 11: Client Update Applies Changes**
    - **Property 12: Client Removal is Complete**
    - **Property 13: Client Group Lifecycle**
    - **Property 14: Client Removal Maintains Referential Integrity**
    - **Property 15: Client Listing is Complete and Accurate**
    - **Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8**

- [x] 5. Implement Policy_Engine component
  - [x] 5.1 Create MAB_Policy data model and PolicyDecision enum
    - Define PolicyDecision enum with ACCEPT_WITH_VLAN, ACCEPT_WITHOUT_VLAN, REJECT
    - Define MAB_Policy class with id, client_group_id, decision, vlan_id, created_at, updated_at
    - Implement VLAN ID validation (1-4094 range)
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 5.2 Implement Policy_Engine interface
    - Implement create_policy, update_policy, delete_policy, get_policy, get_policy_by_client_group, list_policies
    - Implement evaluate_policy(client_group_id) returning (decision, vlan_id)
    - Handle missing policies by returning REJECT (default behavior)
    - Persist changes to policies.json
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.10_
  
  - [x] 5.3 Write property tests for Policy_Engine
    - **Property 16: Policy Creation Maps Client Group to Decision**
    - **Property 17: Policy Accept with VLAN Configuration**
    - **Property 18: Policy Accept without VLAN Configuration**
    - **Property 19: Policy Reject Configuration**
    - **Property 20: Policy Update Applies Changes**
    - **Property 21: Policy Removal is Complete**
    - **Property 22: Policy Listing is Complete and Accurate**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7**

- [x] 6. Implement Log_Manager component
  - [x] 6.1 Create Authentication_Log data model and AuthenticationOutcome enum
    - Define AuthenticationOutcome enum with SUCCESS, FAILURE
    - Define Authentication_Log class with id, timestamp, client_mac, device_id, outcome, vlan_id, created_at
    - _Requirements: 5.1, 5.2, 5.3, 5.4_
  
  - [x] 6.2 Implement Log_Manager interface
    - Implement create_log_entry(client_mac, device_id, outcome, vlan_id) returning Authentication_Log
    - Implement list_logs() returning logs in reverse chronological order
    - Implement filter_logs(date_start, date_end, mac_address, outcome) with all criteria optional
    - Implement get_log_entry(id)
    - Persist changes to logs.json
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.7, 5.8_
  
  - [x] 6.3 Write property tests for Log_Manager
    - **Property 32: Successful Authentication Logging**
    - **Property 33: Failed Authentication Logging**
    - **Property 34: Log Entry Completeness**
    - **Property 35: VLAN Logging**
    - **Property 36: Log Ordering**
    - **Property 37: Log Filtering**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.7, 5.8**

- [x] 7. Implement RADIUS protocol handler
  - [x] 7.1 Create RADIUS packet parser and builder
    - Implement RFC 2865 packet structure parsing (20-byte header, attributes)
    - Implement MD5-based message authentication code (MAC) verification
    - Implement RADIUS attribute encoding/decoding (User-Name, User-Password, Tunnel attributes)
    - _Requirements: 6.3, 6.4_
  
  - [x] 7.2 Implement RADIUS_Server authentication flow
    - Implement UDP listener on port 1812
    - Implement device verification by IP address and shared secret
    - Implement MAC address extraction from User-Name attribute
    - Implement client lookup and group retrieval
    - Implement policy evaluation and response generation
    - Implement Access-Accept and Access-Reject response construction
    - Integrate with Log_Manager to record all authentication attempts
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 5.1, 5.2_
  
  - [x] 7.3 Write property tests for RADIUS protocol
    - **Property 23: RADIUS Request Device Verification**
    - **Property 24: MAC Address Extraction from RADIUS Request**
    - **Property 25: Client Group Lookup**
    - **Property 26: Unknown Client Rejection**
    - **Property 27: Policy Application**
    - **Property 28: Accept with VLAN Response**
    - **Property 29: Accept without VLAN Response**
    - **Property 30: Reject Response**
    - **Property 31: Missing Policy Default Rejection**
    - **Property 38: RFC 2865 Protocol Compliance**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 6.3**

- [x] 8. Implement configuration interface
  - [x] 8.1 Create Flask-based REST API for device management
    - Implement POST /api/devices (create device)
    - Implement PUT /api/devices/{id} (update device)
    - Implement DELETE /api/devices/{id} (delete device)
    - Implement GET /api/devices (list devices)
    - Implement POST /api/device-groups (create group)
    - Implement DELETE /api/device-groups/{id} (delete group)
    - Implement GET /api/device-groups (list groups)
    - _Requirements: 8.1_
  
  - [x] 8.2 Create Flask-based REST API for client management
    - Implement POST /api/clients (create client)
    - Implement PUT /api/clients/{mac} (update client)
    - Implement DELETE /api/clients/{mac} (delete client)
    - Implement GET /api/clients (list clients)
    - Implement POST /api/client-groups (create group)
    - Implement DELETE /api/client-groups/{id} (delete group)
    - Implement GET /api/client-groups (list groups)
    - _Requirements: 8.2_
  
  - [x] 8.3 Create Flask-based REST API for policy management
    - Implement POST /api/policies (create policy)
    - Implement PUT /api/policies/{id} (update policy)
    - Implement DELETE /api/policies/{id} (delete policy)
    - Implement GET /api/policies (list policies)
    - _Requirements: 8.3_
  
  - [x] 8.4 Create Flask-based REST API for log viewing
    - Implement GET /api/logs (list logs with optional filters)
    - Support query parameters: date_start, date_end, mac_address, outcome
    - _Requirements: 8.4_
  
  - [x] 8.5 Implement comprehensive error handling and validation
    - Validate all input data before processing
    - Return descriptive error messages for invalid inputs
    - Handle duplicate IDs/MACs, missing required fields, invalid formats
    - Handle referential integrity violations
    - _Requirements: 8.5, 8.6_
  
  - [x] 8.6 Write property test for configuration validation
    - **Property 44: Configuration Validation**
    - **Validates: Requirements 8.5, 8.6**

- [x] 9. Checkpoint - Ensure all components are integrated
  - Verify all managers are initialized and accessible from RADIUS_Server
  - Verify persistence layer loads data on startup
  - Verify configuration API endpoints are accessible
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Create web UI for configuration interface
  - [x] 10.1 Create HTML/CSS/JavaScript frontend
    - Build device management UI (add/edit/delete devices and groups)
    - Build client management UI (add/edit/delete clients and groups)
    - Build policy management UI (create/edit/delete policies)
    - Build log viewer UI with filtering and visual indicators (green/red)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 5.5, 5.6_
  
  - [x] 10.2 Integrate frontend with REST API
    - Connect UI forms to API endpoints
    - Implement error message display
    - Implement success notifications
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 11. Integration testing and system validation
  - [x] 11.1 Create end-to-end integration tests
    - Test complete authentication flow: device registration → client lookup → policy evaluation → response
    - Test VLAN assignment in responses
    - Test rejection scenarios
    - Test log recording for all scenarios
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 5.1, 5.2_
  
  - [x] 11.2 Write integration tests for data persistence
    - Test server restart with persisted data
    - Test data integrity after restart
    - _Requirements: 7.5_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Run all unit tests, property tests, and integration tests
  - Verify no orphaned code or unused components
  - Ensure all requirements are covered by implementation
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties across all inputs
- Unit tests validate specific examples and edge cases
- Checkpoints ensure incremental validation and early error detection
- All code should follow Python best practices (PEP 8, type hints, docstrings)
- The implementation uses Python 3.8+ with type hints for better code quality
