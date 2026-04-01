"""
Tests for core data models.
"""

import pytest
from datetime import datetime
from src.models import (
    Device,
    DeviceGroup,
    Client,
    ClientGroup,
    MABPolicy,
    AuthenticationLog,
    PolicyDecision,
    AuthenticationOutcome,
    validate_ipv4_address,
    validate_mac_address,
)


class TestModels:
    """Test core data models."""

    def test_device_creation(self):
        """Test Device model creation."""
        device = Device(
            id="switch-01",
            ip_address="192.168.1.1",
            shared_secret="test_secret_123",
            device_group_id="group-1",
        )
        assert device.id == "switch-01"
        assert device.ip_address == "192.168.1.1"
        assert device.shared_secret == "test_secret_123"
        assert device.device_group_id == "group-1"
        assert isinstance(device.created_at, datetime)
        assert isinstance(device.updated_at, datetime)

    def test_device_group_creation(self):
        """Test DeviceGroup model creation."""
        group = DeviceGroup(id="group-1", name="Access Layer")
        assert group.id == "group-1"
        assert group.name == "Access Layer"
        assert isinstance(group.created_at, datetime)
        assert isinstance(group.updated_at, datetime)

    def test_client_creation(self):
        """Test Client model creation."""
        client = Client(
            mac_address="00:11:22:33:44:55",
            client_group_id="client-group-1",
        )
        assert client.mac_address == "00:11:22:33:44:55"
        assert client.client_group_id == "client-group-1"
        assert isinstance(client.created_at, datetime)
        assert isinstance(client.updated_at, datetime)

    def test_client_group_creation(self):
        """Test ClientGroup model creation."""
        group = ClientGroup(id="client-group-1", name="Printers")
        assert group.id == "client-group-1"
        assert group.name == "Printers"
        assert isinstance(group.created_at, datetime)
        assert isinstance(group.updated_at, datetime)

    def test_mab_policy_creation_with_vlan(self):
        """Test MABPolicy model creation with VLAN."""
        policy = MABPolicy(
            id="policy-1",
            client_group_id="client-group-1",
            decision=PolicyDecision.ACCEPT_WITH_VLAN,
            vlan_id=100,
        )
        assert policy.id == "policy-1"
        assert policy.client_group_id == "client-group-1"
        assert policy.decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert policy.vlan_id == 100
        assert isinstance(policy.created_at, datetime)
        assert isinstance(policy.updated_at, datetime)

    def test_mab_policy_creation_without_vlan(self):
        """Test MABPolicy model creation without VLAN."""
        policy = MABPolicy(
            id="policy-2",
            client_group_id="client-group-2",
            decision=PolicyDecision.ACCEPT_WITHOUT_VLAN,
        )
        assert policy.id == "policy-2"
        assert policy.decision == PolicyDecision.ACCEPT_WITHOUT_VLAN
        assert policy.vlan_id is None

    def test_mab_policy_reject(self):
        """Test MABPolicy model with REJECT decision."""
        policy = MABPolicy(
            id="policy-3",
            client_group_id="client-group-3",
            decision=PolicyDecision.REJECT,
        )
        assert policy.decision == PolicyDecision.REJECT

    def test_authentication_log_creation(self):
        """Test AuthenticationLog model creation."""
        now = datetime.utcnow()
        log = AuthenticationLog(
            id="log-1",
            timestamp=now,
            client_mac="00:11:22:33:44:55",
            device_id="switch-01",
            outcome=AuthenticationOutcome.SUCCESS,
            vlan_id=100,
        )
        assert log.id == "log-1"
        assert log.timestamp == now
        assert log.client_mac == "00:11:22:33:44:55"
        assert log.device_id == "switch-01"
        assert log.outcome == AuthenticationOutcome.SUCCESS
        assert log.vlan_id == 100
        assert isinstance(log.created_at, datetime)

    def test_authentication_log_failure(self):
        """Test AuthenticationLog model with FAILURE outcome."""
        log = AuthenticationLog(
            id="log-2",
            timestamp=datetime.utcnow(),
            client_mac="00:11:22:33:44:66",
            device_id="switch-02",
            outcome=AuthenticationOutcome.FAILURE,
        )
        assert log.outcome == AuthenticationOutcome.FAILURE
        assert log.vlan_id is None

    def test_policy_decision_enum(self):
        """Test PolicyDecision enum values."""
        assert PolicyDecision.ACCEPT_WITH_VLAN.value == "accept_with_vlan"
        assert PolicyDecision.ACCEPT_WITHOUT_VLAN.value == "accept_without_vlan"
        assert PolicyDecision.REJECT.value == "reject"

    def test_authentication_outcome_enum(self):
        """Test AuthenticationOutcome enum values."""
        assert AuthenticationOutcome.SUCCESS.value == "success"
        assert AuthenticationOutcome.FAILURE.value == "failure"


class TestIPAddressValidation:
    """Test IP address validation functionality."""

    def test_validate_ipv4_valid_addresses(self):
        """Test validation of valid IPv4 addresses."""
        valid_addresses = [
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "255.255.255.255",
            "0.0.0.0",
            "127.0.0.1",
            "8.8.8.8",
            "1.1.1.1",
        ]
        for addr in valid_addresses:
            assert validate_ipv4_address(addr) is True

    def test_validate_ipv4_invalid_addresses(self):
        """Test validation rejects invalid IPv4 addresses."""
        invalid_addresses = [
            "256.1.1.1",  # Octet > 255
            "192.168.1",  # Missing octet
            "192.168.1.1.1",  # Too many octets
            "192.168.a.1",  # Non-numeric
            "192.168.-1.1",  # Negative number
            "192.168.1.1/24",  # CIDR notation
            "192.168.1.1:8080",  # With port
            "not.an.ip.address",  # Text
            "....",  # Just dots
            "192 168 1 1",  # Spaces instead of dots
        ]
        for addr in invalid_addresses:
            with pytest.raises(ValueError):
                validate_ipv4_address(addr)

    def test_validate_ipv4_empty_string(self):
        """Test validation rejects empty string."""
        with pytest.raises(ValueError, match="IP address cannot be empty"):
            validate_ipv4_address("")

    def test_validate_ipv4_non_string(self):
        """Test validation rejects non-string input."""
        with pytest.raises(ValueError, match="IP address must be a string"):
            validate_ipv4_address(192)
        with pytest.raises(ValueError, match="IP address must be a string"):
            validate_ipv4_address(None)
        with pytest.raises(ValueError, match="IP address must be a string"):
            validate_ipv4_address(["192.168.1.1"])

    def test_device_creation_with_valid_ip(self):
        """Test Device creation with valid IP address."""
        device = Device(
            id="switch-01",
            ip_address="192.168.1.1",
            shared_secret="test_secret_123",
            device_group_id="group-1",
        )
        assert device.ip_address == "192.168.1.1"

    def test_device_creation_with_invalid_ip(self):
        """Test Device creation fails with invalid IP address."""
        with pytest.raises(ValueError):
            Device(
                id="switch-01",
                ip_address="256.256.256.256",
                shared_secret="test_secret_123",
                device_group_id="group-1",
            )

    def test_device_creation_with_empty_ip(self):
        """Test Device creation fails with empty IP address."""
        with pytest.raises(ValueError, match="IP address cannot be empty"):
            Device(
                id="switch-01",
                ip_address="",
                shared_secret="test_secret_123",
                device_group_id="group-1",
            )

    def test_device_creation_with_malformed_ip(self):
        """Test Device creation fails with malformed IP address."""
        with pytest.raises(ValueError):
            Device(
                id="switch-01",
                ip_address="192.168.1",
                shared_secret="test_secret_123",
                device_group_id="group-1",
            )


class TestMACAddressValidation:
    """Test MAC address validation functionality."""

    def test_validate_mac_valid_addresses(self):
        """Test validation of valid MAC addresses."""
        valid_addresses = [
            "00:11:22:33:44:55",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "00:00:00:00:00:00",
            "FF:FF:FF:FF:FF:FF",
            "ff:ff:ff:ff:ff:ff",
            "12:34:56:78:9A:BC",
            "a1:b2:c3:d4:e5:f6",
        ]
        for addr in valid_addresses:
            assert validate_mac_address(addr) is True

    def test_validate_mac_invalid_addresses(self):
        """Test validation rejects invalid MAC addresses."""
        invalid_addresses = [
            "00:11:22:33:44",  # Missing octet
            "00:11:22:33:44:55:66",  # Too many octets
            "00:11:22:33:44:GG",  # Invalid hex character
            "00-11-22-33-44-55",  # Wrong separator
            "00.11.22.33.44.55",  # Wrong separator
            "001122334455",  # No separators
            "00:11:22:33:44:5",  # Missing digit
            "00:11:22:33:44:555",  # Too many digits
            "00:11:22:33:44:55:",  # Trailing separator
            ":00:11:22:33:44:55",  # Leading separator
            "00::11:22:33:44:55",  # Double separator
            "00 11 22 33 44 55",  # Spaces instead of colons
            "not:a:mac:address:at:all",  # Text
            "00:11:22:33:44:5g",  # Invalid hex
            "00:11:22:33:44:5G",  # Invalid hex uppercase
        ]
        for addr in invalid_addresses:
            with pytest.raises(ValueError):
                validate_mac_address(addr)

    def test_validate_mac_empty_string(self):
        """Test validation rejects empty string."""
        with pytest.raises(ValueError, match="MAC address cannot be empty"):
            validate_mac_address("")

    def test_validate_mac_non_string(self):
        """Test validation rejects non-string input."""
        with pytest.raises(ValueError, match="MAC address must be a string"):
            validate_mac_address(123456)
        with pytest.raises(ValueError, match="MAC address must be a string"):
            validate_mac_address(None)
        with pytest.raises(ValueError, match="MAC address must be a string"):
            validate_mac_address(["00:11:22:33:44:55"])

    def test_client_creation_with_valid_mac(self):
        """Test Client creation with valid MAC address."""
        client = Client(
            mac_address="00:11:22:33:44:55",
            client_group_id="client-group-1",
        )
        assert client.mac_address == "00:11:22:33:44:55"

    def test_client_creation_with_uppercase_mac(self):
        """Test Client creation with uppercase MAC address."""
        client = Client(
            mac_address="AA:BB:CC:DD:EE:FF",
            client_group_id="client-group-1",
        )
        assert client.mac_address == "AA:BB:CC:DD:EE:FF"

    def test_client_creation_with_mixed_case_mac(self):
        """Test Client creation with mixed case MAC address."""
        client = Client(
            mac_address="aA:bB:cC:dD:eE:fF",
            client_group_id="client-group-1",
        )
        assert client.mac_address == "aA:bB:cC:dD:eE:fF"

    def test_client_creation_with_invalid_mac(self):
        """Test Client creation fails with invalid MAC address."""
        with pytest.raises(ValueError):
            Client(
                mac_address="00:11:22:33:44",
                client_group_id="client-group-1",
            )

    def test_client_creation_with_empty_mac(self):
        """Test Client creation fails with empty MAC address."""
        with pytest.raises(ValueError, match="MAC address cannot be empty"):
            Client(
                mac_address="",
                client_group_id="client-group-1",
            )

    def test_client_creation_with_malformed_mac(self):
        """Test Client creation fails with malformed MAC address."""
        with pytest.raises(ValueError):
            Client(
                mac_address="00-11-22-33-44-55",
                client_group_id="client-group-1",
            )

    def test_client_creation_with_invalid_hex_mac(self):
        """Test Client creation fails with invalid hex characters in MAC."""
        with pytest.raises(ValueError):
            Client(
                mac_address="00:11:22:33:44:GG",
                client_group_id="client-group-1",
            )
