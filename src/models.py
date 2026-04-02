"""
Core data models and type hints for the RADIUS server.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid
import re


def validate_ipv4_address(ip_address: str) -> bool:
    """
    Validate that a string is a valid IPv4 address.
    
    Args:
        ip_address: String to validate as IPv4 address
        
    Returns:
        True if valid IPv4 format, False otherwise
        
    Raises:
        ValueError: If ip_address is not a valid IPv4 address
    """
    if not isinstance(ip_address, str):
        raise ValueError("IP address must be a string")
    
    if not ip_address:
        raise ValueError("IP address cannot be empty")
    
    # IPv4 regex pattern: matches X.X.X.X where X is 0-255
    ipv4_pattern = r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
    
    if not re.match(ipv4_pattern, ip_address):
        raise ValueError(f"Invalid IPv4 address format: {ip_address}")
    
    return True


def validate_mac_address(mac_address: str) -> str:
    """
    Validate and normalize a MAC address to XX:XX:XX:XX:XX:XX format.
    Accepts multiple input formats: colon, dash, dot, or no separator.
    
    Args:
        mac_address: String to validate as MAC address
        
    Returns:
        Normalized MAC address in XX:XX:XX:XX:XX:XX format
        
    Raises:
        ValueError: If mac_address is not a valid MAC address
    """
    if not isinstance(mac_address, str):
        raise ValueError("MAC address must be a string")
    
    if not mac_address:
        raise ValueError("MAC address cannot be empty")
    
    # Remove common separators and convert to lowercase
    normalized = mac_address.replace(':', '').replace('-', '').replace('.', '').lower()
    
    # Check if it's 12 hex characters
    if not re.match(r'^[0-9a-f]{12}$', normalized):
        raise ValueError(f"Invalid MAC address format: {mac_address}. Expected 12 hexadecimal characters (with or without separators)")
    
    # Convert to colon-separated format
    return ':'.join(normalized[i:i+2] for i in range(0, 12, 2))


class PolicyDecision(Enum):
    """Enumeration of possible policy decisions."""
    ACCEPT_WITH_VLAN = "accept_with_vlan"
    ACCEPT_WITHOUT_VLAN = "accept_without_vlan"
    REJECT = "reject"


class AuthenticationOutcome(Enum):
    """Enumeration of authentication outcomes."""
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass
class Device:
    """Represents a network device that sends RADIUS requests."""
    name: str
    ip_address: str
    shared_secret: str
    device_group_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate device attributes after initialization."""
        validate_ipv4_address(self.ip_address)


@dataclass
class DeviceGroup:
    """Represents a logical collection of devices."""
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Client:
    """Represents an endpoint device identified by MAC address."""
    mac_address: str
    client_group_name: str
    name: str = ""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Validate and normalize client attributes after initialization."""
        self.mac_address = validate_mac_address(self.mac_address)


@dataclass
class ClientGroup:
    """Represents a logical collection of clients."""
    name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class MABPolicy:
    """Represents a policy that maps client groups to authentication decisions."""
    name: str
    client_group_name: str
    decision: PolicyDecision
    vlan_id: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AuthenticationLog:
    """Represents an audit record of an authentication attempt."""
    id: str
    timestamp: datetime
    client_mac: str
    device_id: str
    outcome: AuthenticationOutcome
    vlan_id: Optional[int] = None
    policy_name: Optional[str] = None
    policy_decision: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
