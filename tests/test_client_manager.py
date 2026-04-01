"""
Unit tests for Client_Manager component.

Tests cover:
- Client creation, update, deletion, and retrieval
- Client group creation, deletion, and retrieval
- MAC address validation
- One-to-one Client-to-ClientGroup relationship enforcement
- Referential integrity constraints
- Persistence of client data
- Error handling and descriptive error messages
"""

import pytest
import tempfile
import os
from datetime import datetime
from src.client_manager import (
    Client_Manager,
    ClientManagerError,
    ClientNotFoundError,
    ClientGroupNotFoundError,
    DuplicateClientError,
    DuplicateClientGroupError,
    ReferentialIntegrityError,
    InvalidMACAddressError,
)
from src.models import Client, ClientGroup


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config(temp_dir, monkeypatch):
    """Mock the config module to use temporary directory."""
    # Use the actual temp_dir for all config files
    devices_file = os.path.join(temp_dir, "devices.json")
    clients_file = os.path.join(temp_dir, "clients.json")
    policies_file = os.path.join(temp_dir, "policies.json")
    logs_file = os.path.join(temp_dir, "logs.json")
    
    # Patch the config module
    monkeypatch.setattr("config.config.DEVICES_FILE", devices_file)
    monkeypatch.setattr("config.config.CLIENTS_FILE", clients_file)
    monkeypatch.setattr("config.config.POLICIES_FILE", policies_file)
    monkeypatch.setattr("config.config.LOGS_FILE", logs_file)
    
    # Also patch in persistence module since it's already imported
    import src.persistence
    monkeypatch.setattr("src.persistence.DEVICES_FILE", devices_file)
    monkeypatch.setattr("src.persistence.CLIENTS_FILE", clients_file)
    monkeypatch.setattr("src.persistence.POLICIES_FILE", policies_file)
    monkeypatch.setattr("src.persistence.LOGS_FILE", logs_file)
    
    return temp_dir


@pytest.fixture
def manager(mock_config):
    """Create a fresh Client_Manager instance for each test."""
    return Client_Manager()


class TestClientCreation:
    """Tests for client creation functionality."""
    
    def test_create_client_with_valid_inputs(self, manager):
        """Test creating a client with valid MAC address and group."""
        # Setup: Create a client group first
        manager.create_client_group("group1", "Test Group")
        
        # Execute: Create a client
        client = manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        # Verify
        assert client.mac_address == "AA:BB:CC:DD:EE:FF"
        assert client.client_group_id == "group1"
        assert client.created_at is not None
        assert client.updated_at is not None
    
    def test_create_client_duplicate_mac_raises_error(self, manager):
        """Test that creating a client with duplicate MAC raises error."""
        manager.create_client_group("group1", "Test Group")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        with pytest.raises(DuplicateClientError) as exc_info:
            manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_client_nonexistent_group_raises_error(self, manager):
        """Test that creating a client with nonexistent group raises error."""
        with pytest.raises(ClientGroupNotFoundError) as exc_info:
            manager.create_client("AA:BB:CC:DD:EE:FF", "nonexistent")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_create_client_invalid_mac_raises_error(self, manager):
        """Test that creating a client with invalid MAC format raises error."""
        manager.create_client_group("group1", "Test Group")
        
        with pytest.raises(InvalidMACAddressError) as exc_info:
            manager.create_client("invalid-mac", "group1")
        
        assert "Invalid MAC address format" in str(exc_info.value)
    
    def test_create_client_persists_to_storage(self, manager, mock_config):
        """Test that created clients are persisted to storage."""
        manager.create_client_group("group1", "Test Group")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        # Create new manager instance to verify persistence
        new_manager = Client_Manager()
        client = new_manager.get_client("AA:BB:CC:DD:EE:FF")
        
        assert client is not None
        assert client.mac_address == "AA:BB:CC:DD:EE:FF"
        assert client.client_group_id == "group1"


class TestClientUpdate:
    """Tests for client update functionality."""
    
    def test_update_client_group_assignment(self, manager):
        """Test updating a client's group assignment."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client_group("group2", "Group 2")
        client = manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        updated = manager.update_client("AA:BB:CC:DD:EE:FF", "group2")
        
        assert updated.client_group_id == "group2"
        assert updated.mac_address == "AA:BB:CC:DD:EE:FF"
    
    def test_update_nonexistent_client_raises_error(self, manager):
        """Test that updating nonexistent client raises error."""
        with pytest.raises(ClientNotFoundError) as exc_info:
            manager.update_client("AA:BB:CC:DD:EE:FF", "group1")
        
        assert "not found" in str(exc_info.value)
    
    def test_update_client_invalid_group_raises_error(self, manager):
        """Test that updating to nonexistent group raises error."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        with pytest.raises(ClientGroupNotFoundError) as exc_info:
            manager.update_client("AA:BB:CC:DD:EE:FF", "nonexistent")
        
        assert "does not exist" in str(exc_info.value)
    
    def test_update_client_updates_timestamp(self, manager):
        """Test that updating a client updates its timestamp."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client_group("group2", "Group 2")
        client = manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        original_updated_at = client.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        updated = manager.update_client("AA:BB:CC:DD:EE:FF", "group2")
        
        assert updated.updated_at > original_updated_at


class TestClientDeletion:
    """Tests for client deletion functionality."""
    
    def test_delete_client(self, manager):
        """Test deleting a client."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        manager.delete_client("AA:BB:CC:DD:EE:FF")
        
        assert manager.get_client("AA:BB:CC:DD:EE:FF") is None
    
    def test_delete_nonexistent_client_raises_error(self, manager):
        """Test that deleting nonexistent client raises error."""
        with pytest.raises(ClientNotFoundError) as exc_info:
            manager.delete_client("AA:BB:CC:DD:EE:FF")
        
        assert "not found" in str(exc_info.value)
    
    def test_delete_client_persists(self, manager, mock_config):
        """Test that client deletion is persisted."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        manager.delete_client("AA:BB:CC:DD:EE:FF")
        
        # Create new manager instance to verify persistence
        new_manager = Client_Manager()
        assert new_manager.get_client("AA:BB:CC:DD:EE:FF") is None


class TestClientRetrieval:
    """Tests for client retrieval functionality."""
    
    def test_get_client_by_mac(self, manager):
        """Test retrieving a client by MAC address."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        client = manager.get_client("AA:BB:CC:DD:EE:FF")
        
        assert client is not None
        assert client.mac_address == "AA:BB:CC:DD:EE:FF"
    
    def test_get_nonexistent_client_returns_none(self, manager):
        """Test that getting nonexistent client returns None."""
        client = manager.get_client("AA:BB:CC:DD:EE:FF")
        assert client is None
    
    def test_list_clients(self, manager):
        """Test listing all clients."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        manager.create_client("11:22:33:44:55:66", "group1")
        
        clients = manager.list_clients()
        
        assert len(clients) == 2
        macs = {c.mac_address for c in clients}
        assert "AA:BB:CC:DD:EE:FF" in macs
        assert "11:22:33:44:55:66" in macs
    
    def test_list_clients_empty(self, manager):
        """Test listing clients when none exist."""
        clients = manager.list_clients()
        assert clients == []


class TestClientGroupCreation:
    """Tests for client group creation functionality."""
    
    def test_create_client_group(self, manager):
        """Test creating a client group."""
        group = manager.create_client_group("group1", "Test Group")
        
        assert group.id == "group1"
        assert group.name == "Test Group"
        assert group.created_at is not None
    
    def test_create_client_group_duplicate_id_raises_error(self, manager):
        """Test that creating group with duplicate ID raises error."""
        manager.create_client_group("group1", "Group 1")
        
        with pytest.raises(DuplicateClientGroupError) as exc_info:
            manager.create_client_group("group1", "Group 2")
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_client_group_persists(self, manager, mock_config):
        """Test that created groups are persisted."""
        manager.create_client_group("group1", "Test Group")
        
        new_manager = Client_Manager()
        group = new_manager.get_client_group("group1")
        
        assert group is not None
        assert group.id == "group1"
        assert group.name == "Test Group"


class TestClientGroupDeletion:
    """Tests for client group deletion functionality."""
    
    def test_delete_client_group(self, manager):
        """Test deleting a client group."""
        manager.create_client_group("group1", "Group 1")
        
        manager.delete_client_group("group1")
        
        assert manager.get_client_group("group1") is None
    
    def test_delete_nonexistent_group_raises_error(self, manager):
        """Test that deleting nonexistent group raises error."""
        with pytest.raises(ClientGroupNotFoundError) as exc_info:
            manager.delete_client_group("nonexistent")
        
        assert "not found" in str(exc_info.value)
    
    def test_delete_group_with_clients_raises_error(self, manager):
        """Test that deleting group with assigned clients raises error."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        with pytest.raises(ReferentialIntegrityError) as exc_info:
            manager.delete_client_group("group1")
        
        assert "assigned clients" in str(exc_info.value)
    
    def test_delete_group_after_removing_clients(self, manager):
        """Test that group can be deleted after removing all clients."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        manager.delete_client("AA:BB:CC:DD:EE:FF")
        
        # Should not raise error
        manager.delete_client_group("group1")
        
        assert manager.get_client_group("group1") is None
    
    def test_delete_group_persists(self, manager, mock_config):
        """Test that group deletion is persisted."""
        manager.create_client_group("group1", "Group 1")
        manager.delete_client_group("group1")
        
        new_manager = Client_Manager()
        assert new_manager.get_client_group("group1") is None


class TestClientGroupRetrieval:
    """Tests for client group retrieval functionality."""
    
    def test_get_client_group_by_id(self, manager):
        """Test retrieving a client group by ID."""
        manager.create_client_group("group1", "Test Group")
        
        group = manager.get_client_group("group1")
        
        assert group is not None
        assert group.id == "group1"
        assert group.name == "Test Group"
    
    def test_get_nonexistent_group_returns_none(self, manager):
        """Test that getting nonexistent group returns None."""
        group = manager.get_client_group("nonexistent")
        assert group is None
    
    def test_list_client_groups(self, manager):
        """Test listing all client groups."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client_group("group2", "Group 2")
        
        groups = manager.list_client_groups()
        
        assert len(groups) == 2
        ids = {g.id for g in groups}
        assert "group1" in ids
        assert "group2" in ids
    
    def test_list_client_groups_empty(self, manager):
        """Test listing groups when none exist."""
        groups = manager.list_client_groups()
        assert groups == []


class TestOneToOneRelationship:
    """Tests for one-to-one Client-to-ClientGroup relationship."""
    
    def test_client_assigned_to_exactly_one_group(self, manager):
        """Test that each client is assigned to exactly one group."""
        manager.create_client_group("group1", "Group 1")
        client = manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        assert client.client_group_id == "group1"
        # Verify it's not assigned to multiple groups
        assert len([g for g in manager.list_client_groups() 
                   if client.client_group_id == g.id]) == 1
    
    def test_client_group_assignment_immutable_until_updated(self, manager):
        """Test that client group assignment is immutable until explicitly updated."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client_group("group2", "Group 2")
        client = manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        # Verify initial assignment
        assert client.client_group_id == "group1"
        
        # Verify it doesn't change without explicit update
        retrieved = manager.get_client("AA:BB:CC:DD:EE:FF")
        assert retrieved.client_group_id == "group1"
        
        # Update and verify change
        updated = manager.update_client("AA:BB:CC:DD:EE:FF", "group2")
        assert updated.client_group_id == "group2"


class TestReferentialIntegrity:
    """Tests for referential integrity constraints."""
    
    def test_cannot_create_client_with_nonexistent_group(self, manager):
        """Test that creating client with nonexistent group fails."""
        with pytest.raises(ClientGroupNotFoundError):
            manager.create_client("AA:BB:CC:DD:EE:FF", "nonexistent")
    
    def test_cannot_update_client_to_nonexistent_group(self, manager):
        """Test that updating client to nonexistent group fails."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        with pytest.raises(ClientGroupNotFoundError):
            manager.update_client("AA:BB:CC:DD:EE:FF", "nonexistent")
    
    def test_cannot_delete_group_with_assigned_clients(self, manager):
        """Test that deleting group with clients fails."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        with pytest.raises(ReferentialIntegrityError):
            manager.delete_client_group("group1")
    
    def test_client_removal_maintains_consistency(self, manager):
        """Test that removing a client maintains system consistency."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        manager.create_client("11:22:33:44:55:66", "group1")
        
        manager.delete_client("AA:BB:CC:DD:EE:FF")
        
        # Verify group still exists
        assert manager.get_client_group("group1") is not None
        # Verify other client still exists
        assert manager.get_client("11:22:33:44:55:66") is not None
        # Verify deleted client is gone
        assert manager.get_client("AA:BB:CC:DD:EE:FF") is None


class TestPersistence:
    """Tests for persistence functionality."""
    
    def test_clients_persisted_across_instances(self, manager, mock_config):
        """Test that clients persist across manager instances."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        manager.create_client("11:22:33:44:55:66", "group1")
        
        new_manager = Client_Manager()
        clients = new_manager.list_clients()
        
        assert len(clients) == 2
        macs = {c.mac_address for c in clients}
        assert "AA:BB:CC:DD:EE:FF" in macs
        assert "11:22:33:44:55:66" in macs
    
    def test_client_groups_persisted_across_instances(self, manager, mock_config):
        """Test that client groups persist across manager instances."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client_group("group2", "Group 2")
        
        new_manager = Client_Manager()
        groups = new_manager.list_client_groups()
        
        assert len(groups) == 2
        ids = {g.id for g in groups}
        assert "group1" in ids
        assert "group2" in ids
    
    def test_complex_state_persisted(self, manager, mock_config):
        """Test that complex state with multiple clients and groups persists."""
        manager.create_client_group("printers", "Printers")
        manager.create_client_group("laptops", "Laptops")
        manager.create_client("AA:BB:CC:DD:EE:FF", "printers")
        manager.create_client("11:22:33:44:55:66", "laptops")
        manager.create_client("99:88:77:66:55:44", "printers")
        
        new_manager = Client_Manager()
        
        # Verify groups
        assert new_manager.get_client_group("printers") is not None
        assert new_manager.get_client_group("laptops") is not None
        
        # Verify clients and their assignments
        printer_client = new_manager.get_client("AA:BB:CC:DD:EE:FF")
        assert printer_client.client_group_id == "printers"
        
        laptop_client = new_manager.get_client("11:22:33:44:55:66")
        assert laptop_client.client_group_id == "laptops"


class TestMACAddressValidation:
    """Tests for MAC address validation."""
    
    def test_valid_mac_addresses_accepted(self, manager):
        """Test that valid MAC addresses are accepted."""
        manager.create_client_group("group1", "Group 1")
        
        valid_macs = [
            "00:00:00:00:00:00",
            "FF:FF:FF:FF:FF:FF",
            "AA:BB:CC:DD:EE:FF",
            "aa:bb:cc:dd:ee:ff",
            "12:34:56:78:9A:BC",
        ]
        
        for mac in valid_macs:
            client = manager.create_client(mac, "group1")
            assert client.mac_address == mac
    
    def test_invalid_mac_addresses_rejected(self, manager):
        """Test that invalid MAC addresses are rejected."""
        manager.create_client_group("group1", "Group 1")
        
        invalid_macs = [
            "invalid",
            "AA:BB:CC:DD:EE",  # Too short
            "AA:BB:CC:DD:EE:FF:00",  # Too long
            "AA-BB-CC-DD-EE-FF",  # Wrong separator
            "AABBCCDDEEFF",  # No separators
            "AA:BB:CC:DD:EE:GG",  # Invalid hex
            "",  # Empty
        ]
        
        for mac in invalid_macs:
            with pytest.raises(InvalidMACAddressError):
                manager.create_client(mac, "group1")
    
    def test_validate_mac_address_method(self, manager):
        """Test the validate_mac_address method."""
        assert manager.validate_mac_address("AA:BB:CC:DD:EE:FF") is True
        
        with pytest.raises(InvalidMACAddressError):
            manager.validate_mac_address("invalid")


class TestErrorHandling:
    """Tests for error handling and descriptive error messages."""
    
    def test_error_messages_are_descriptive(self, manager):
        """Test that error messages are descriptive."""
        manager.create_client_group("group1", "Group 1")
        manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
        
        # Test duplicate client error
        try:
            manager.create_client("AA:BB:CC:DD:EE:FF", "group1")
            assert False, "Should have raised DuplicateClientError"
        except DuplicateClientError as e:
            assert "AA:BB:CC:DD:EE:FF" in str(e)
            assert "already exists" in str(e)
        
        # Test nonexistent group error
        try:
            manager.create_client("11:22:33:44:55:66", "nonexistent")
            assert False, "Should have raised ClientGroupNotFoundError"
        except ClientGroupNotFoundError as e:
            assert "nonexistent" in str(e)
            assert "does not exist" in str(e)
        
        # Test referential integrity error
        try:
            manager.delete_client_group("group1")
            assert False, "Should have raised ReferentialIntegrityError"
        except ReferentialIntegrityError as e:
            assert "group1" in str(e)
            assert "assigned clients" in str(e)


# ============================================================
# Property-Based Tests
# ============================================================

import tempfile as _tempfile
import os as _os
from unittest.mock import patch as _patch
import src.persistence as _persistence_mod
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from datetime import datetime as _dt_cls


_text_id = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00/\\"),
    min_size=1,
    max_size=30,
)

_mac_octet = st.integers(min_value=0, max_value=255)
_mac_address_st = st.builds(
    lambda octets: ":".join(f"{b:02X}" for b in octets),
    st.lists(_mac_octet, min_size=6, max_size=6),
)

# Strings that are NOT valid MAC addresses (for Property 10 negative tests)
_invalid_mac_st = st.one_of(
    st.just(""),
    st.just("AA:BB:CC:DD:EE"),          # too short
    st.just("AA:BB:CC:DD:EE:FF:00"),    # too long
    st.just("AA-BB-CC-DD-EE-FF"),       # wrong separator
    st.just("AABBCCDDEEFF"),            # no separators
    st.just("ZZ:BB:CC:DD:EE:FF"),       # invalid hex
)


def _fresh_client_manager():
    """Context manager: yields a Client_Manager backed by a fresh temp dir."""
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with _tempfile.TemporaryDirectory() as d:
            with _patch.object(_persistence_mod, "DEVICES_FILE", _os.path.join(d, "devices.json")), \
                 _patch.object(_persistence_mod, "CLIENTS_FILE", _os.path.join(d, "clients.json")), \
                 _patch.object(_persistence_mod, "POLICIES_FILE", _os.path.join(d, "policies.json")), \
                 _patch.object(_persistence_mod, "LOGS_FILE", _os.path.join(d, "logs.json")):
                yield Client_Manager()

    return _ctx()


class TestPropertyMACAddressValidation:
    """
    Property 10: MAC Address Validation
    Validates: Requirements 2.3
    """

    @settings(max_examples=100)
    @given(octets=st.lists(_mac_octet, min_size=6, max_size=6))
    def test_valid_mac_addresses_accepted(self, octets):
        """
        Feature: simple-radius-server, Property 10: MAC Address Validation

        Any string matching XX:XX:XX:XX:XX:XX (hex digits) SHALL pass validation.
        """
        mac = ":".join(f"{b:02X}" for b in octets)
        with _fresh_client_manager() as mgr:
            result = mgr.validate_mac_address(mac)
        assert result is True

    @settings(max_examples=50)
    @given(invalid_mac=_invalid_mac_st)
    def test_invalid_mac_addresses_rejected(self, invalid_mac):
        """
        Feature: simple-radius-server, Property 10: MAC Address Validation

        Any string NOT matching XX:XX:XX:XX:XX:XX SHALL fail validation.
        """
        with _fresh_client_manager() as mgr:
            try:
                mgr.validate_mac_address(invalid_mac)
                assert False, f"Expected InvalidMACAddressError for '{invalid_mac}'"
            except InvalidMACAddressError:
                pass


class TestPropertyClientManager:
    """
    Properties 8-9, 11-15: Client_Manager correctness properties
    Validates: Requirements 2.1, 2.2, 2.4, 2.5, 2.6, 2.7, 2.8
    """

    @settings(max_examples=50)
    @given(group_id=_text_id, group_name=_text_id, mac=_mac_address_st)
    def test_property8_client_creation_with_mac_address(self, group_id, group_name, mac):
        """
        Feature: simple-radius-server, Property 8: Client Creation with MAC Address

        Created client SHALL have the MAC address as unique identifier and specified group.
        """
        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            client = mgr.create_client(mac, group_id)

        assert client.mac_address == mac
        assert client.client_group_id == group_id

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, mac=_mac_address_st)
    def test_property9_client_group_assignment_one_to_one(self, group_id, group_name, mac):
        """
        Feature: simple-radius-server, Property 9: Client-Group Assignment is One-to-One
        """
        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            mgr.create_client(mac, group_id)
            client = mgr.get_client(mac)
            assignments = [c.client_group_id for c in mgr.list_clients() if c.mac_address == mac]

        assert client.client_group_id == group_id
        assert len(assignments) == 1

    @settings(max_examples=30)
    @given(group_id1=_text_id, group_id2=_text_id, group_name=_text_id, mac=_mac_address_st)
    def test_property11_client_update_applies_changes(self, group_id1, group_id2, group_name, mac):
        """
        Feature: simple-radius-server, Property 11: Client Update Applies Changes
        """
        assume(group_id1 != group_id2)

        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id1, group_name)
            mgr.create_client_group(group_id2, group_name)
            mgr.create_client(mac, group_id1)
            mgr.update_client(mac, group_id2)
            updated = mgr.get_client(mac)

        assert updated.client_group_id == group_id2

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, mac=_mac_address_st)
    def test_property12_client_removal_is_complete(self, group_id, group_name, mac):
        """
        Feature: simple-radius-server, Property 12: Client Removal is Complete
        """
        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            mgr.create_client(mac, group_id)
            mgr.delete_client(mac)
            found = mgr.get_client(mac)
            listed = [c.mac_address for c in mgr.list_clients()]

        assert found is None
        assert mac not in listed

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id)
    def test_property13_client_group_lifecycle(self, group_id, group_name):
        """
        Feature: simple-radius-server, Property 13: Client Group Lifecycle
        """
        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            after_create = mgr.get_client_group(group_id) is not None
            mgr.delete_client_group(group_id)
            after_delete = mgr.get_client_group(group_id) is not None

        assert after_create is True
        assert after_delete is False

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id,
           mac1=_mac_address_st, mac2=_mac_address_st)
    def test_property14_client_removal_maintains_referential_integrity(
        self, group_id, group_name, mac1, mac2
    ):
        """
        Feature: simple-radius-server, Property 14: Client Removal Maintains Referential Integrity
        """
        assume(mac1 != mac2)

        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            mgr.create_client(mac1, group_id)
            mgr.create_client(mac2, group_id)
            mgr.delete_client(mac1)
            remaining = mgr.get_client(mac2)
            group_exists = mgr.get_client_group(group_id) is not None

        assert remaining is not None
        assert remaining.client_group_id == group_id
        assert group_exists

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id,
           macs=st.lists(_mac_address_st, min_size=1, max_size=5, unique=True))
    def test_property15_client_listing_is_complete_and_accurate(self, group_id, group_name, macs):
        """
        Feature: simple-radius-server, Property 15: Client Listing is Complete and Accurate
        """
        with _fresh_client_manager() as mgr:
            mgr.create_client_group(group_id, group_name)
            created = set()
            for mac in macs:
                mgr.create_client(mac, group_id)
                created.add(mac)
            listed = {c.mac_address for c in mgr.list_clients()}

        assert listed == created
