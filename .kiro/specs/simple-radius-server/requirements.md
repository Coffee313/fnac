# Requirements Document

## Introduction

This document specifies the requirements for a Simple RADIUS Server system that provides network access control through MAC Authentication Bypass (MAB). The system manages network devices, authenticates clients based on MAC addresses, applies policy-based VLAN assignments, and maintains audit logs of authentication events. The system is designed to run on Debian-based operating systems, specifically tested on Astra Linux 1.7.5.

## Glossary

- **RADIUS_Server**: The authentication server that processes RADIUS authentication requests
- **Device**: A network device (switch, access point, etc.) that sends RADIUS authentication requests to the RADIUS_Server
- **Client**: An endpoint device identified by its MAC address that attempts to authenticate via MAB
- **Device_Group**: A logical collection of Devices with shared configuration
- **Client_Group**: A logical collection of Clients with shared policy attributes
- **MAB**: MAC Authentication Bypass - authentication method using MAC address as credentials
- **MAB_Policy**: A rule that defines authentication response behavior for a Client_Group
- **VLAN_ID**: Virtual LAN identifier assigned to authenticated clients
- **Access_Accept**: RADIUS response indicating successful authentication
- **Access_Reject**: RADIUS response indicating failed authentication
- **Authentication_Log**: Audit record of authentication attempts and outcomes
- **Device_Manager**: Component responsible for managing Device and Device_Group data
- **Client_Manager**: Component responsible for managing Client and Client_Group data
- **Policy_Engine**: Component that evaluates MAB_Policy rules and determines authentication responses
- **Log_Manager**: Component that records and displays Authentication_Log entries

## Requirements

### Requirement 1: Device Management

**User Story:** As a network administrator, I want to add and organize network devices into groups, so that I can manage which devices are authorized to send RADIUS requests.

#### Acceptance Criteria

1. THE Device_Manager SHALL create a new Device with a unique identifier, IP address, and shared secret
2. THE Device_Manager SHALL assign a Device to exactly one Device_Group
3. THE Device_Manager SHALL update Device attributes including IP address and shared secret
4. THE Device_Manager SHALL remove a Device from the system
5. THE Device_Manager SHALL create and delete Device_Group entities
6. WHEN a Device is removed, THE Device_Manager SHALL maintain referential integrity by handling the removal appropriately
7. THE Device_Manager SHALL list all Devices and their assigned Device_Group

### Requirement 2: Client Management

**User Story:** As a network administrator, I want to add MAC addresses and organize them into groups, so that I can control which endpoints can access the network.

#### Acceptance Criteria

1. THE Client_Manager SHALL create a new Client with a MAC address as the unique identifier
2. THE Client_Manager SHALL assign a Client to exactly one Client_Group
3. THE Client_Manager SHALL validate MAC address format before creating a Client
4. THE Client_Manager SHALL update Client attributes including assigned Client_Group
5. THE Client_Manager SHALL remove a Client from the system
6. THE Client_Manager SHALL create and delete Client_Group entities
7. WHEN a Client is removed, THE Client_Manager SHALL maintain referential integrity by handling the removal appropriately
8. THE Client_Manager SHALL list all Clients and their assigned Client_Group

### Requirement 3: MAB Policy Configuration

**User Story:** As a network administrator, I want to define authentication policies for client groups, so that I can control network access and VLAN assignments based on client identity.

#### Acceptance Criteria

1. THE Policy_Engine SHALL create a MAB_Policy that maps a Client_Group to an authentication decision
2. THE Policy_Engine SHALL configure a MAB_Policy to return Access_Accept with a specified VLAN_ID
3. THE Policy_Engine SHALL configure a MAB_Policy to return Access_Accept without VLAN_ID assignment
4. THE Policy_Engine SHALL configure a MAB_Policy to return Access_Reject
5. THE Policy_Engine SHALL update existing MAB_Policy rules
6. THE Policy_Engine SHALL delete MAB_Policy rules
7. THE Policy_Engine SHALL list all configured MAB_Policy rules with their associated Client_Group and response behavior

### Requirement 4: RADIUS Authentication Processing

**User Story:** As a network administrator, I want the server to process RADIUS authentication requests using MAB, so that clients can be authenticated based on their MAC address.

#### Acceptance Criteria

1. WHEN a RADIUS authentication request is received, THE RADIUS_Server SHALL verify the request originates from a registered Device
2. WHEN a request is from an unregistered Device, THE RADIUS_Server SHALL reject the request
3. WHEN a request is from a registered Device, THE RADIUS_Server SHALL extract the Client MAC address from the request
4. WHEN a Client MAC address is found in the Client_Manager, THE RADIUS_Server SHALL retrieve the associated Client_Group
5. WHEN a Client MAC address is not found in the Client_Manager, THE RADIUS_Server SHALL return Access_Reject
6. WHEN a Client_Group has an associated MAB_Policy, THE RADIUS_Server SHALL apply the policy to generate the authentication response
7. WHEN a MAB_Policy specifies Access_Accept with VLAN_ID, THE RADIUS_Server SHALL include the VLAN_ID attribute in the Access_Accept response
8. WHEN a MAB_Policy specifies Access_Accept without VLAN_ID, THE RADIUS_Server SHALL return Access_Accept without VLAN attributes
9. WHEN a MAB_Policy specifies Access_Reject, THE RADIUS_Server SHALL return Access_Reject
10. WHEN no MAB_Policy exists for a Client_Group, THE RADIUS_Server SHALL return Access_Reject

### Requirement 5: Authentication Logging

**User Story:** As a network administrator, I want to view logs of authentication events with visual indicators, so that I can audit network access and troubleshoot authentication issues.

#### Acceptance Criteria

1. WHEN the RADIUS_Server sends Access_Accept, THE Log_Manager SHALL create an Authentication_Log entry marked as successful
2. WHEN the RADIUS_Server sends Access_Reject, THE Log_Manager SHALL create an Authentication_Log entry marked as failed
3. THE Log_Manager SHALL record the timestamp, Client MAC address, Device identifier, and authentication outcome in each Authentication_Log entry
4. WHEN a VLAN_ID is assigned, THE Log_Manager SHALL include the VLAN_ID in the Authentication_Log entry
5. THE Log_Manager SHALL display successful authentication events with a green visual indicator
6. THE Log_Manager SHALL display failed authentication events with a red visual indicator
7. THE Log_Manager SHALL list Authentication_Log entries in reverse chronological order
8. THE Log_Manager SHALL filter Authentication_Log entries by date range, Client MAC address, or outcome

### Requirement 6: Platform Compatibility

**User Story:** As a system administrator, I want the RADIUS server to run on Debian-based systems, so that I can deploy it on my existing infrastructure.

#### Acceptance Criteria

1. THE RADIUS_Server SHALL run on Debian-based operating systems
2. THE RADIUS_Server SHALL be tested and verified on Astra Linux 1.7.5
3. THE RADIUS_Server SHALL use standard RADIUS protocol (RFC 2865) for authentication
4. THE RADIUS_Server SHALL listen on the standard RADIUS authentication port (UDP 1812)

### Requirement 7: Data Persistence

**User Story:** As a network administrator, I want all configuration and logs to persist across server restarts, so that I don't lose my setup when the server is restarted.

#### Acceptance Criteria

1. THE RADIUS_Server SHALL persist all Device and Device_Group data
2. THE RADIUS_Server SHALL persist all Client and Client_Group data
3. THE RADIUS_Server SHALL persist all MAB_Policy configurations
4. THE RADIUS_Server SHALL persist all Authentication_Log entries
5. WHEN the RADIUS_Server starts, THE RADIUS_Server SHALL load all persisted data before accepting authentication requests

### Requirement 8: Configuration Interface

**User Story:** As a network administrator, I want an interface to configure the RADIUS server, so that I can manage devices, clients, and policies without editing configuration files manually.

#### Acceptance Criteria

1. THE RADIUS_Server SHALL provide a configuration interface for managing Devices and Device_Groups
2. THE RADIUS_Server SHALL provide a configuration interface for managing Clients and Client_Groups
3. THE RADIUS_Server SHALL provide a configuration interface for managing MAB_Policy rules
4. THE RADIUS_Server SHALL provide an interface for viewing Authentication_Log entries
5. WHEN invalid data is submitted through the interface, THE RADIUS_Server SHALL return descriptive error messages
6. THE RADIUS_Server SHALL validate all configuration changes before applying them

