"""
Comprehensive tests for Device_Manager component.

Tests cover:
- Device creation, update, deletion, and retrieval
- Device group creation and deletion
- One-to-one Device-to-Device_Group relationship enforcement
- Referential integrity constraints
- Persistence of changes
- Error handling and validation
"""

import pytest
from datetime import datetime
from src.device_manager import (
    Device_Manager,
    DeviceManagerError,
    DeviceNotFoundError,
    DeviceGroupNotFoundError,
    DuplicateDeviceError,
    DuplicateDeviceGroupError,
    ReferentialIntegrityError,
)
from src.models import Device, DeviceGroup
from src.persistence import DevicePersistence
from unittest.mock import patch, MagicMock
import tempfile
import os


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
    """Create a fresh Device_Manager instance for each test."""
    # Create a new instance - it will load from the temp directory
    return Device_Manager()


class TestDeviceCreation:
    """Tests for device creation functionality."""
    
    def test_create_device_with_valid_inputs(self, manager):
        """Test creating a device with valid inputs."""
        # Setup: Create a device group first
        manager.create_device_group("group1", "Access Layer")
        
        # Execute: Create a device
        device = manager.create_device(
            device_id="switch-01",
            ip_address="192.168.1.1",
            shared_secret="secret123",
            device_group_id="group1"
        )
        
        # Verify
        assert device.id == "switch-01"
        assert device.ip_address == "192.168.1.1"
        assert device.shared_secret == "secret123"
        assert device.device_group_id == "group1"
        assert isinstance(device.created_at, datetime)
        assert isinstance(device.updated_at, datetime)
    
    def test_create_device_duplicate_id_raises_error(self, manager):
        """Test that creating a device with duplicate ID raises error."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        with pytest.raises(DuplicateDeviceError) as exc_info:
            manager.create_device("switch-01", "192.168.1.2", "secret456", "group1")
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_device_nonexistent_group_raises_error(self, manager):
        """Test that creating a device with nonexistent group raises error."""
        with pytest.raises(DeviceGroupNotFoundError) as exc_info:
            manager.create_device(
                "switch-01",
                "192.168.1.1",
                "secret123",
                "nonexistent-group"
            )
        
        assert "does not exist" in str(exc_info.value)
    
    def test_create_device_invalid_ip_raises_error(self, manager):
        """Test that creating a device with invalid IP raises error."""
        manager.create_device_group("group1", "Access Layer")
        
        with pytest.raises(ValueError):
            manager.create_device(
                "switch-01",
                "invalid-ip",
                "secret123",
                "group1"
            )
    
    def test_create_device_persists_to_storage(self, manager, mock_config):
        """Test that created device is persisted to storage."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        # Create new manager instance to verify persistence
        new_manager = Device_Manager()
        device = new_manager.get_device("switch-01")
        
        assert device is not None
        assert device.id == "switch-01"
        assert device.ip_address == "192.168.1.1"


class TestDeviceUpdate:
    """Tests for device update functionality."""
    
    def test_update_device_ip_address(self, manager):
        """Test updating a device's IP address."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        updated = manager.update_device("switch-01", ip_address="192.168.1.2")
        
        assert updated.ip_address == "192.168.1.2"
        assert updated.shared_secret == "secret123"
    
    def test_update_device_shared_secret(self, manager):
        """Test updating a device's shared secret."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        updated = manager.update_device("switch-01", shared_secret="newsecret456")
        
        assert updated.shared_secret == "newsecret456"
        assert updated.ip_address == "192.168.1.1"
    
    def test_update_device_group_assignment(self, manager):
        """Test updating a device's group assignment."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device_group("group2", "Distribution Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        updated = manager.update_device("switch-01", device_group_id="group2")
        
        assert updated.device_group_id == "group2"
    
    def test_update_device_multiple_attributes(self, manager):
        """Test updating multiple device attributes at once."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device_group("group2", "Distribution Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        updated = manager.update_device(
            "switch-01",
            ip_address="192.168.1.2",
            shared_secret="newsecret",
            device_group_id="group2"
        )
        
        assert updated.ip_address == "192.168.1.2"
        assert updated.shared_secret == "newsecret"
        assert updated.device_group_id == "group2"
    
    def test_update_nonexistent_device_raises_error(self, manager):
        """Test that updating nonexistent device raises error."""
        with pytest.raises(DeviceNotFoundError):
            manager.update_device("nonexistent", ip_address="192.168.1.1")
    
    def test_update_device_invalid_group_raises_error(self, manager):
        """Test that updating device with invalid group raises error."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        with pytest.raises(DeviceGroupNotFoundError):
            manager.update_device("switch-01", device_group_id="nonexistent")
    
    def test_update_device_invalid_ip_raises_error(self, manager):
        """Test that updating device with invalid IP raises error."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        with pytest.raises(ValueError):
            manager.update_device("switch-01", ip_address="invalid-ip")
    
    def test_update_device_updates_timestamp(self, manager):
        """Test that updating device updates the updated_at timestamp."""
        manager.create_device_group("group1", "Access Layer")
        device = manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        original_updated_at = device.updated_at
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        updated = manager.update_device("switch-01", ip_address="192.168.1.2")
        
        assert updated.updated_at > original_updated_at


class TestDeviceDeletion:
    """Tests for device deletion functionality."""
    
    def test_delete_device(self, manager):
        """Test deleting a device."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        manager.delete_device("switch-01")
        
        assert manager.get_device("switch-01") is None
    
    def test_delete_nonexistent_device_raises_error(self, manager):
        """Test that deleting nonexistent device raises error."""
        with pytest.raises(DeviceNotFoundError):
            manager.delete_device("nonexistent")
    
    def test_delete_device_persists(self, manager):
        """Test that device deletion is persisted."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        manager.delete_device("switch-01")
        
        # Create new manager to verify persistence
        new_manager = Device_Manager()
        assert new_manager.get_device("switch-01") is None


class TestDeviceRetrieval:
    """Tests for device retrieval functionality."""
    
    def test_get_device_by_id(self, manager):
        """Test retrieving a device by ID."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        device = manager.get_device("switch-01")
        
        assert device is not None
        assert device.id == "switch-01"
    
    def test_get_nonexistent_device_returns_none(self, manager):
        """Test that getting nonexistent device returns None."""
        device = manager.get_device("nonexistent")
        assert device is None
    
    def test_get_device_by_ip(self, manager):
        """Test retrieving a device by IP address."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        device = manager.get_device_by_ip("192.168.1.1")
        
        assert device is not None
        assert device.id == "switch-01"
    
    def test_get_device_by_nonexistent_ip_returns_none(self, manager):
        """Test that getting device by nonexistent IP returns None."""
        device = manager.get_device_by_ip("192.168.1.99")
        assert device is None
    
    def test_list_devices(self, manager):
        """Test listing all devices."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        manager.create_device("switch-02", "192.168.1.2", "secret456", "group1")
        
        devices = manager.list_devices()
        
        assert len(devices) == 2
        assert any(d.id == "switch-01" for d in devices)
        assert any(d.id == "switch-02" for d in devices)
    
    def test_list_devices_empty(self, manager):
        """Test listing devices when none exist."""
        devices = manager.list_devices()
        assert devices == []


class TestDeviceGroupCreation:
    """Tests for device group creation functionality."""
    
    def test_create_device_group(self, manager):
        """Test creating a device group."""
        group = manager.create_device_group("group1", "Access Layer")
        
        assert group.id == "group1"
        assert group.name == "Access Layer"
        assert isinstance(group.created_at, datetime)
    
    def test_create_device_group_duplicate_id_raises_error(self, manager):
        """Test that creating group with duplicate ID raises error."""
        manager.create_device_group("group1", "Access Layer")
        
        with pytest.raises(DuplicateDeviceGroupError) as exc_info:
            manager.create_device_group("group1", "Distribution Layer")
        
        assert "already exists" in str(exc_info.value)
    
    def test_create_device_group_persists(self, manager):
        """Test that device group creation is persisted."""
        manager.create_device_group("group1", "Access Layer")
        
        new_manager = Device_Manager()
        group = new_manager.get_device_group("group1")
        
        assert group is not None
        assert group.name == "Access Layer"


class TestDeviceGroupDeletion:
    """Tests for device group deletion functionality."""
    
    def test_delete_device_group(self, manager):
        """Test deleting an empty device group."""
        manager.create_device_group("group1", "Access Layer")
        
        manager.delete_device_group("group1")
        
        assert manager.get_device_group("group1") is None
    
    def test_delete_nonexistent_group_raises_error(self, manager):
        """Test that deleting nonexistent group raises error."""
        with pytest.raises(DeviceGroupNotFoundError):
            manager.delete_device_group("nonexistent")
    
    def test_delete_group_with_devices_raises_error(self, manager):
        """Test that deleting group with assigned devices raises error."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        with pytest.raises(ReferentialIntegrityError) as exc_info:
            manager.delete_device_group("group1")
        
        assert "assigned devices" in str(exc_info.value)
    
    def test_delete_group_after_removing_devices(self, manager):
        """Test that group can be deleted after removing all devices."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        manager.delete_device("switch-01")
        manager.delete_device_group("group1")
        
        assert manager.get_device_group("group1") is None
    
    def test_delete_group_persists(self, manager):
        """Test that group deletion is persisted."""
        manager.create_device_group("group1", "Access Layer")
        manager.delete_device_group("group1")
        
        new_manager = Device_Manager()
        assert new_manager.get_device_group("group1") is None


class TestDeviceGroupRetrieval:
    """Tests for device group retrieval functionality."""
    
    def test_get_device_group_by_id(self, manager):
        """Test retrieving a device group by ID."""
        manager.create_device_group("group1", "Access Layer")
        
        group = manager.get_device_group("group1")
        
        assert group is not None
        assert group.id == "group1"
    
    def test_get_nonexistent_group_returns_none(self, manager):
        """Test that getting nonexistent group returns None."""
        group = manager.get_device_group("nonexistent")
        assert group is None
    
    def test_list_device_groups(self, manager):
        """Test listing all device groups."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device_group("group2", "Distribution Layer")
        
        groups = manager.list_device_groups()
        
        assert len(groups) == 2
        assert any(g.id == "group1" for g in groups)
        assert any(g.id == "group2" for g in groups)
    
    def test_list_device_groups_empty(self, manager):
        """Test listing groups when none exist."""
        groups = manager.list_device_groups()
        assert groups == []


class TestOneToOneRelationship:
    """Tests for one-to-one Device-to-Device_Group relationship."""
    
    def test_device_assigned_to_exactly_one_group(self, manager):
        """Test that each device is assigned to exactly one group."""
        manager.create_device_group("group1", "Access Layer")
        device = manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        assert device.device_group_id == "group1"
        
        # Verify it's not assigned to multiple groups
        groups = manager.list_device_groups()
        assigned_groups = [g.id for g in groups if any(
            d.device_group_id == g.id for d in manager.list_devices()
        )]
        assert assigned_groups.count("group1") == 1
    
    def test_device_group_assignment_immutable_until_updated(self, manager):
        """Test that device group assignment is immutable until explicitly updated."""
        manager.create_device_group("group1", "Access Layer")
        device = manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        # Get device again without updating
        retrieved = manager.get_device("switch-01")
        assert retrieved.device_group_id == "group1"
        
        # Update to different group
        manager.create_device_group("group2", "Distribution Layer")
        updated = manager.update_device("switch-01", device_group_id="group2")
        assert updated.device_group_id == "group2"


class TestReferentialIntegrity:
    """Tests for referential integrity constraints."""
    
    def test_cannot_create_device_with_nonexistent_group(self, manager):
        """Test that device cannot be created with nonexistent group."""
        with pytest.raises(DeviceGroupNotFoundError):
            manager.create_device(
                "switch-01",
                "192.168.1.1",
                "secret123",
                "nonexistent-group"
            )
    
    def test_cannot_update_device_to_nonexistent_group(self, manager):
        """Test that device cannot be updated to nonexistent group."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        with pytest.raises(DeviceGroupNotFoundError):
            manager.update_device("switch-01", device_group_id="nonexistent")
    
    def test_cannot_delete_group_with_assigned_devices(self, manager):
        """Test that group with assigned devices cannot be deleted."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        manager.create_device("switch-02", "192.168.1.2", "secret456", "group1")
        
        with pytest.raises(ReferentialIntegrityError):
            manager.delete_device_group("group1")
    
    def test_device_removal_maintains_consistency(self, manager):
        """Test that device removal maintains system consistency."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        manager.create_device("switch-02", "192.168.1.2", "secret456", "group1")
        
        manager.delete_device("switch-01")
        
        # Verify remaining device still has valid group
        remaining = manager.get_device("switch-02")
        assert remaining.device_group_id == "group1"
        
        # Verify group still exists
        group = manager.get_device_group("group1")
        assert group is not None


class TestPersistence:
    """Tests for persistence functionality."""
    
    def test_devices_persisted_across_instances(self, manager):
        """Test that devices are persisted across manager instances."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        
        new_manager = Device_Manager()
        device = new_manager.get_device("switch-01")
        
        assert device is not None
        assert device.ip_address == "192.168.1.1"
    
    def test_device_groups_persisted_across_instances(self, manager):
        """Test that device groups are persisted across manager instances."""
        manager.create_device_group("group1", "Access Layer")
        
        new_manager = Device_Manager()
        group = new_manager.get_device_group("group1")
        
        assert group is not None
        assert group.name == "Access Layer"
    
    def test_complex_state_persisted(self, manager):
        """Test that complex state with multiple devices and groups is persisted."""
        manager.create_device_group("group1", "Access Layer")
        manager.create_device_group("group2", "Distribution Layer")
        manager.create_device("switch-01", "192.168.1.1", "secret123", "group1")
        manager.create_device("switch-02", "192.168.1.2", "secret456", "group2")
        
        new_manager = Device_Manager()
        
        assert len(new_manager.list_devices()) == 2
        assert len(new_manager.list_device_groups()) == 2
        assert new_manager.get_device("switch-01").device_group_id == "group1"
        assert new_manager.get_device("switch-02").device_group_id == "group2"


class TestErrorHandling:
    """Tests for error handling and validation."""
    
    def test_invalid_ipv4_address_rejected(self, manager):
        """Test that invalid IPv4 addresses are rejected."""
        manager.create_device_group("group1", "Access Layer")
        
        invalid_ips = [
            "256.1.1.1",
            "192.168.1",
            "192.168.1.1.1",
            "abc.def.ghi.jkl",
            "",
        ]
        
        for invalid_ip in invalid_ips:
            with pytest.raises(ValueError):
                manager.create_device(
                    "switch-01",
                    invalid_ip,
                    "secret123",
                    "group1"
                )
    
    def test_valid_ipv4_addresses_accepted(self, manager):
        """Test that valid IPv4 addresses are accepted."""
        manager.create_device_group("group1", "Access Layer")
        
        valid_ips = [
            "0.0.0.0",
            "192.168.1.1",
            "255.255.255.255",
            "10.0.0.1",
        ]
        
        for i, valid_ip in enumerate(valid_ips):
            device = manager.create_device(
                f"switch-{i:02d}",
                valid_ip,
                "secret123",
                "group1"
            )
            assert device.ip_address == valid_ip


# ============================================================
# Property-Based Tests
# ============================================================

import tempfile as _tempfile
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

_ipv4 = st.builds(
    lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
)

_secret = st.text(min_size=1, max_size=50,
                  alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"))


def _fresh_manager():
    """Context manager: yields a Device_Manager backed by a fresh temp dir."""
    import contextlib, os

    @contextlib.contextmanager
    def _ctx():
        with _tempfile.TemporaryDirectory() as d:
            with _patch.object(_persistence_mod, "DEVICES_FILE", os.path.join(d, "devices.json")), \
                 _patch.object(_persistence_mod, "CLIENTS_FILE", os.path.join(d, "clients.json")), \
                 _patch.object(_persistence_mod, "POLICIES_FILE", os.path.join(d, "policies.json")), \
                 _patch.object(_persistence_mod, "LOGS_FILE", os.path.join(d, "logs.json")):
                yield Device_Manager()

    return _ctx()


class TestPropertyDeviceCreation:
    """
    Property 1: Device Creation Preserves Attributes
    Validates: Requirements 1.1
    """

    @settings(max_examples=50)
    @given(
        group_id=_text_id,
        group_name=_text_id,
        device_id=_text_id,
        ip=_ipv4,
        secret=_secret,
    )
    def test_device_creation_preserves_attributes(self, group_id, group_name, device_id, ip, secret):
        """
        Feature: simple-radius-server, Property 1: Device Creation Preserves Attributes
        """
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            device = mgr.create_device(device_id, ip, secret, group_id)

        assert device.id == device_id
        assert device.ip_address == ip
        assert device.shared_secret == secret
        assert device.device_group_id == group_id
        assert isinstance(device.created_at, _dt_cls)
        assert isinstance(device.updated_at, _dt_cls)


class TestPropertyDeviceManager:
    """
    Properties 2-7: Device_Manager correctness properties
    Validates: Requirements 1.2, 1.3, 1.4, 1.5, 1.6, 1.7
    """

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, device_id=_text_id, ip=_ipv4, secret=_secret)
    def test_property2_device_group_assignment_one_to_one(self, group_id, group_name, device_id, ip, secret):
        """Feature: simple-radius-server, Property 2: Device-Group Assignment is One-to-One"""
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            mgr.create_device(device_id, ip, secret, group_id)
            device = mgr.get_device(device_id)
            assignments = [d.device_group_id for d in mgr.list_devices() if d.id == device_id]

        assert device.device_group_id == group_id
        assert len(assignments) == 1

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, device_id=_text_id,
           ip=_ipv4, secret=_secret, new_ip=_ipv4, new_secret=_secret)
    def test_property3_device_update_applies_changes(self, group_id, group_name, device_id, ip, secret, new_ip, new_secret):
        """Feature: simple-radius-server, Property 3: Device Update Applies Changes"""
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            mgr.create_device(device_id, ip, secret, group_id)
            mgr.update_device(device_id, ip_address=new_ip, shared_secret=new_secret)
            updated = mgr.get_device(device_id)

        assert updated.ip_address == new_ip
        assert updated.shared_secret == new_secret

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, device_id=_text_id, ip=_ipv4, secret=_secret)
    def test_property4_device_removal_is_complete(self, group_id, group_name, device_id, ip, secret):
        """Feature: simple-radius-server, Property 4: Device Removal is Complete"""
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            mgr.create_device(device_id, ip, secret, group_id)
            mgr.delete_device(device_id)
            found = mgr.get_device(device_id)
            listed = [d.id for d in mgr.list_devices()]

        assert found is None
        assert device_id not in listed

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id)
    def test_property5_device_group_lifecycle(self, group_id, group_name):
        """Feature: simple-radius-server, Property 5: Device Group Lifecycle"""
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            after_create = mgr.get_device_group(group_id) is not None
            mgr.delete_device_group(group_id)
            after_delete = mgr.get_device_group(group_id) is not None

        assert after_create is True
        assert after_delete is False

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id, device_id1=_text_id, device_id2=_text_id,
           ip1=_ipv4, ip2=_ipv4, secret=_secret)
    def test_property6_device_removal_maintains_referential_integrity(
        self, group_id, group_name, device_id1, device_id2, ip1, ip2, secret
    ):
        """Feature: simple-radius-server, Property 6: Device Removal Maintains Referential Integrity"""
        assume(device_id1 != device_id2)
        assume(ip1 != ip2)

        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            mgr.create_device(device_id1, ip1, secret, group_id)
            mgr.create_device(device_id2, ip2, secret, group_id)
            mgr.delete_device(device_id1)
            remaining = mgr.get_device(device_id2)
            group_exists = mgr.get_device_group(group_id) is not None

        assert remaining is not None
        assert remaining.device_group_id == group_id
        assert group_exists

    @settings(max_examples=30)
    @given(group_id=_text_id, group_name=_text_id,
           device_ids=st.lists(_text_id, min_size=1, max_size=5, unique=True), secret=_secret)
    def test_property7_device_listing_is_complete_and_accurate(self, group_id, group_name, device_ids, secret):
        """Feature: simple-radius-server, Property 7: Device Listing is Complete and Accurate"""
        with _fresh_manager() as mgr:
            mgr.create_device_group(group_id, group_name)
            created_ids = set()
            for i, did in enumerate(device_ids):
                mgr.create_device(did, f"10.0.{i // 256}.{i % 256}", secret, group_id)
                created_ids.add(did)
            listed_ids = {d.id for d in mgr.list_devices()}

        assert listed_ids == created_ids
