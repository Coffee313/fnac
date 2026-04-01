"""
Tests for the persistence layer.

Tests atomic file write operations, load/save functions, and data validation.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.models import (
    AuthenticationLog,
    AuthenticationOutcome,
    Client,
    ClientGroup,
    Device,
    DeviceGroup,
    MABPolicy,
    PolicyDecision,
)
from src.persistence import (
    AtomicFileWriter,
    ClientPersistence,
    DataValidationError,
    DevicePersistence,
    LogPersistence,
    PersistenceError,
    PolicyPersistence,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_config(temp_dir, monkeypatch):
    """Mock config paths to use temporary directory."""
    # Patch the persistence module's imports
    monkeypatch.setattr("src.persistence.DEVICES_FILE", os.path.join(temp_dir, "devices.json"))
    monkeypatch.setattr("src.persistence.CLIENTS_FILE", os.path.join(temp_dir, "clients.json"))
    monkeypatch.setattr("src.persistence.POLICIES_FILE", os.path.join(temp_dir, "policies.json"))
    monkeypatch.setattr("src.persistence.LOGS_FILE", os.path.join(temp_dir, "logs.json"))
    yield temp_dir


class TestAtomicFileWriter:
    """Tests for atomic file write operations."""

    def test_write_atomic_creates_file(self, temp_dir):
        """Test that atomic write creates a file."""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value"}

        AtomicFileWriter.write_atomic(file_path, data)

        assert os.path.exists(file_path)
        with open(file_path, 'r') as f:
            loaded = json.load(f)
        assert loaded == data

    def test_write_atomic_creates_parent_directories(self, temp_dir):
        """Test that atomic write creates parent directories."""
        file_path = os.path.join(temp_dir, "subdir", "nested", "test.json")
        data = {"key": "value"}

        AtomicFileWriter.write_atomic(file_path, data)

        assert os.path.exists(file_path)

    def test_write_atomic_overwrites_existing_file(self, temp_dir):
        """Test that atomic write overwrites existing files."""
        file_path = os.path.join(temp_dir, "test.json")
        
        # Write initial data
        AtomicFileWriter.write_atomic(file_path, {"old": "data"})
        
        # Overwrite with new data
        new_data = {"new": "data"}
        AtomicFileWriter.write_atomic(file_path, new_data)

        with open(file_path, 'r') as f:
            loaded = json.load(f)
        assert loaded == new_data

    def test_write_atomic_serializes_datetime(self, temp_dir):
        """Test that atomic write serializes datetime objects."""
        file_path = os.path.join(temp_dir, "test.json")
        now = datetime.utcnow()
        data = {"timestamp": now}

        AtomicFileWriter.write_atomic(file_path, data)

        with open(file_path, 'r') as f:
            loaded = json.load(f)
        assert loaded["timestamp"] == now.isoformat()

    def test_write_atomic_serializes_enums(self, temp_dir):
        """Test that atomic write serializes enum values."""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"decision": PolicyDecision.ACCEPT_WITH_VLAN}

        AtomicFileWriter.write_atomic(file_path, data)

        with open(file_path, 'r') as f:
            loaded = json.load(f)
        assert loaded["decision"] == "accept_with_vlan"

    def test_write_atomic_no_temp_files_left(self, temp_dir):
        """Test that atomic write doesn't leave temp files."""
        file_path = os.path.join(temp_dir, "test.json")
        data = {"key": "value"}

        AtomicFileWriter.write_atomic(file_path, data)

        # Check no temp files exist
        temp_files = [f for f in os.listdir(temp_dir) if f.startswith(".tmp_")]
        assert len(temp_files) == 0


class TestDevicePersistence:
    """Tests for device persistence."""

    def test_save_and_load_devices(self, mock_config):
        """Test saving and loading devices."""
        device_group = DeviceGroup(id="group1", name="Access Layer")
        device = Device(
            id="switch-01",
            ip_address="192.168.1.1",
            shared_secret="secret123",
            device_group_id="group1"
        )

        DevicePersistence.save([device], [device_group])
        loaded_devices, loaded_groups = DevicePersistence.load()

        assert len(loaded_devices) == 1
        assert len(loaded_groups) == 1
        assert loaded_devices[0].id == "switch-01"
        assert loaded_groups[0].id == "group1"

    def test_load_empty_when_file_not_exists(self, mock_config):
        """Test that load returns empty lists when file doesn't exist."""
        devices, groups = DevicePersistence.load()
        assert devices == []
        assert groups == []

    def test_save_multiple_devices(self, mock_config):
        """Test saving multiple devices."""
        group1 = DeviceGroup(id="group1", name="Group 1")
        group2 = DeviceGroup(id="group2", name="Group 2")
        device1 = Device(
            id="dev1",
            ip_address="192.168.1.1",
            shared_secret="secret1",
            device_group_id="group1"
        )
        device2 = Device(
            id="dev2",
            ip_address="192.168.1.2",
            shared_secret="secret2",
            device_group_id="group2"
        )

        DevicePersistence.save([device1, device2], [group1, group2])
        loaded_devices, loaded_groups = DevicePersistence.load()

        assert len(loaded_devices) == 2
        assert len(loaded_groups) == 2

    def test_load_corrupted_json_raises_error(self, mock_config, monkeypatch):
        """Test that corrupted JSON raises DataValidationError."""
        devices_file = os.path.join(mock_config, "devices.json")
        # Write corrupted JSON
        with open(devices_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(DataValidationError):
            DevicePersistence.load()

    def test_load_missing_required_fields_raises_error(self, mock_config):
        """Test that missing required fields raises DataValidationError."""
        devices_file = os.path.join(mock_config, "devices.json")
        # Write JSON with missing fields
        data = {
            "devices": [{"id": "dev1"}],  # Missing other required fields
            "device_groups": []
        }
        with open(devices_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(DataValidationError):
            DevicePersistence.load()

    def test_load_invalid_device_id_raises_error(self, mock_config):
        """Test that invalid device ID raises DataValidationError."""
        devices_file = os.path.join(mock_config, "devices.json")
        data = {
            "devices": [{
                "id": "",  # Empty ID
                "ip_address": "192.168.1.1",
                "shared_secret": "secret",
                "device_group_id": "group1",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }],
            "device_groups": []
        }
        with open(devices_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(DataValidationError):
            DevicePersistence.load()

    def test_preserves_timestamps(self, mock_config):
        """Test that timestamps are preserved during save/load."""
        now = datetime.utcnow()
        device_group = DeviceGroup(
            id="group1",
            name="Group",
            created_at=now,
            updated_at=now
        )
        device = Device(
            id="dev1",
            ip_address="192.168.1.1",
            shared_secret="secret",
            device_group_id="group1",
            created_at=now,
            updated_at=now
        )

        DevicePersistence.save([device], [device_group])
        loaded_devices, loaded_groups = DevicePersistence.load()

        assert loaded_devices[0].created_at == now
        assert loaded_groups[0].created_at == now


class TestClientPersistence:
    """Tests for client persistence."""

    def test_save_and_load_clients(self, mock_config):
        """Test saving and loading clients."""
        client_group = ClientGroup(id="group1", name="Printers")
        client = Client(
            mac_address="AA:BB:CC:DD:EE:FF",
            client_group_id="group1"
        )

        ClientPersistence.save([client], [client_group])
        loaded_clients, loaded_groups = ClientPersistence.load()

        assert len(loaded_clients) == 1
        assert len(loaded_groups) == 1
        assert loaded_clients[0].mac_address == "AA:BB:CC:DD:EE:FF"
        assert loaded_groups[0].id == "group1"

    def test_load_empty_when_file_not_exists(self, mock_config):
        """Test that load returns empty lists when file doesn't exist."""
        clients, groups = ClientPersistence.load()
        assert clients == []
        assert groups == []

    def test_save_multiple_clients(self, mock_config):
        """Test saving multiple clients."""
        group = ClientGroup(id="group1", name="Group")
        client1 = Client(mac_address="AA:BB:CC:DD:EE:01", client_group_id="group1")
        client2 = Client(mac_address="AA:BB:CC:DD:EE:02", client_group_id="group1")

        ClientPersistence.save([client1, client2], [group])
        loaded_clients, _ = ClientPersistence.load()

        assert len(loaded_clients) == 2

    def test_load_corrupted_json_raises_error(self, mock_config):
        """Test that corrupted JSON raises DataValidationError."""
        clients_file = os.path.join(mock_config, "clients.json")
        with open(clients_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(DataValidationError):
            ClientPersistence.load()

    def test_load_missing_required_fields_raises_error(self, mock_config):
        """Test that missing required fields raises DataValidationError."""
        clients_file = os.path.join(mock_config, "clients.json")
        data = {
            "clients": [{"mac_address": "AA:BB:CC:DD:EE:FF"}],  # Missing client_group_id
            "client_groups": []
        }
        with open(clients_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(DataValidationError):
            ClientPersistence.load()


class TestPolicyPersistence:
    """Tests for policy persistence."""

    def test_save_and_load_policies(self, mock_config):
        """Test saving and loading policies."""
        policy = MABPolicy(
            id="policy1",
            client_group_id="group1",
            decision=PolicyDecision.ACCEPT_WITH_VLAN,
            vlan_id=100
        )

        PolicyPersistence.save([policy])
        loaded_policies = PolicyPersistence.load()

        assert len(loaded_policies) == 1
        assert loaded_policies[0].id == "policy1"
        assert loaded_policies[0].decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert loaded_policies[0].vlan_id == 100

    def test_load_empty_when_file_not_exists(self, mock_config):
        """Test that load returns empty list when file doesn't exist."""
        policies = PolicyPersistence.load()
        assert policies == []

    def test_save_policy_without_vlan(self, mock_config):
        """Test saving policy without VLAN."""
        policy = MABPolicy(
            id="policy1",
            client_group_id="group1",
            decision=PolicyDecision.ACCEPT_WITHOUT_VLAN,
            vlan_id=None
        )

        PolicyPersistence.save([policy])
        loaded_policies = PolicyPersistence.load()

        assert loaded_policies[0].vlan_id is None

    def test_save_reject_policy(self, mock_config):
        """Test saving reject policy."""
        policy = MABPolicy(
            id="policy1",
            client_group_id="group1",
            decision=PolicyDecision.REJECT
        )

        PolicyPersistence.save([policy])
        loaded_policies = PolicyPersistence.load()

        assert loaded_policies[0].decision == PolicyDecision.REJECT

    def test_load_corrupted_json_raises_error(self, mock_config):
        """Test that corrupted JSON raises DataValidationError."""
        policies_file = os.path.join(mock_config, "policies.json")
        with open(policies_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(DataValidationError):
            PolicyPersistence.load()

    def test_load_invalid_decision_raises_error(self, mock_config):
        """Test that invalid decision raises DataValidationError."""
        policies_file = os.path.join(mock_config, "policies.json")
        data = {
            "policies": [{
                "id": "policy1",
                "client_group_id": "group1",
                "decision": "invalid_decision",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            }]
        }
        with open(policies_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(DataValidationError):
            PolicyPersistence.load()


class TestLogPersistence:
    """Tests for log persistence."""

    def test_save_and_load_logs(self, mock_config):
        """Test saving and loading logs."""
        log = AuthenticationLog(
            id="log1",
            timestamp=datetime.utcnow(),
            client_mac="AA:BB:CC:DD:EE:FF",
            device_id="switch-01",
            outcome=AuthenticationOutcome.SUCCESS,
            vlan_id=100
        )

        LogPersistence.save([log])
        loaded_logs = LogPersistence.load()

        assert len(loaded_logs) == 1
        assert loaded_logs[0].id == "log1"
        assert loaded_logs[0].outcome == AuthenticationOutcome.SUCCESS
        assert loaded_logs[0].vlan_id == 100

    def test_load_empty_when_file_not_exists(self, mock_config):
        """Test that load returns empty list when file doesn't exist."""
        logs = LogPersistence.load()
        assert logs == []

    def test_save_failure_log(self, mock_config):
        """Test saving failure log."""
        log = AuthenticationLog(
            id="log1",
            timestamp=datetime.utcnow(),
            client_mac="AA:BB:CC:DD:EE:FF",
            device_id="switch-01",
            outcome=AuthenticationOutcome.FAILURE,
            vlan_id=None
        )

        LogPersistence.save([log])
        loaded_logs = LogPersistence.load()

        assert loaded_logs[0].outcome == AuthenticationOutcome.FAILURE
        assert loaded_logs[0].vlan_id is None

    def test_save_multiple_logs(self, mock_config):
        """Test saving multiple logs."""
        log1 = AuthenticationLog(
            id="log1",
            timestamp=datetime.utcnow(),
            client_mac="AA:BB:CC:DD:EE:01",
            device_id="switch-01",
            outcome=AuthenticationOutcome.SUCCESS
        )
        log2 = AuthenticationLog(
            id="log2",
            timestamp=datetime.utcnow(),
            client_mac="AA:BB:CC:DD:EE:02",
            device_id="switch-01",
            outcome=AuthenticationOutcome.FAILURE
        )

        LogPersistence.save([log1, log2])
        loaded_logs = LogPersistence.load()

        assert len(loaded_logs) == 2

    def test_load_corrupted_json_raises_error(self, mock_config):
        """Test that corrupted JSON raises DataValidationError."""
        logs_file = os.path.join(mock_config, "logs.json")
        with open(logs_file, 'w') as f:
            f.write("{invalid json")

        with pytest.raises(DataValidationError):
            LogPersistence.load()

    def test_load_invalid_outcome_raises_error(self, mock_config):
        """Test that invalid outcome raises DataValidationError."""
        logs_file = os.path.join(mock_config, "logs.json")
        data = {
            "logs": [{
                "id": "log1",
                "timestamp": datetime.utcnow().isoformat(),
                "client_mac": "AA:BB:CC:DD:EE:FF",
                "device_id": "switch-01",
                "outcome": "invalid_outcome",
                "created_at": datetime.utcnow().isoformat(),
            }]
        }
        with open(logs_file, 'w') as f:
            json.dump(data, f)

        with pytest.raises(DataValidationError):
            LogPersistence.load()


class TestPersistenceRoundTrip:
    """Tests for complete round-trip persistence (write then read)."""

    def test_device_round_trip_preserves_all_data(self, mock_config):
        """Test that device data is preserved through save/load cycle."""
        now = datetime.utcnow()
        group = DeviceGroup(id="g1", name="Group 1", created_at=now, updated_at=now)
        device = Device(
            id="d1",
            ip_address="192.168.1.1",
            shared_secret="secret123",
            device_group_id="g1",
            created_at=now,
            updated_at=now
        )

        DevicePersistence.save([device], [group])
        loaded_devices, loaded_groups = DevicePersistence.load()

        assert loaded_devices[0].id == device.id
        assert loaded_devices[0].ip_address == device.ip_address
        assert loaded_devices[0].shared_secret == device.shared_secret
        assert loaded_devices[0].device_group_id == device.device_group_id

    def test_client_round_trip_preserves_all_data(self, mock_config):
        """Test that client data is preserved through save/load cycle."""
        now = datetime.utcnow()
        group = ClientGroup(id="g1", name="Group 1", created_at=now, updated_at=now)
        client = Client(
            mac_address="AA:BB:CC:DD:EE:FF",
            client_group_id="g1",
            created_at=now,
            updated_at=now
        )

        ClientPersistence.save([client], [group])
        loaded_clients, loaded_groups = ClientPersistence.load()

        assert loaded_clients[0].mac_address == client.mac_address
        assert loaded_clients[0].client_group_id == client.client_group_id

    def test_policy_round_trip_preserves_all_data(self, mock_config):
        """Test that policy data is preserved through save/load cycle."""
        now = datetime.utcnow()
        policy = MABPolicy(
            id="p1",
            client_group_id="g1",
            decision=PolicyDecision.ACCEPT_WITH_VLAN,
            vlan_id=100,
            created_at=now,
            updated_at=now
        )

        PolicyPersistence.save([policy])
        loaded_policies = PolicyPersistence.load()

        assert loaded_policies[0].id == policy.id
        assert loaded_policies[0].client_group_id == policy.client_group_id
        assert loaded_policies[0].decision == policy.decision
        assert loaded_policies[0].vlan_id == policy.vlan_id

    def test_log_round_trip_preserves_all_data(self, mock_config):
        """Test that log data is preserved through save/load cycle."""
        now = datetime.utcnow()
        log = AuthenticationLog(
            id="l1",
            timestamp=now,
            client_mac="AA:BB:CC:DD:EE:FF",
            device_id="d1",
            outcome=AuthenticationOutcome.SUCCESS,
            vlan_id=100,
            created_at=now
        )

        LogPersistence.save([log])
        loaded_logs = LogPersistence.load()

        assert loaded_logs[0].id == log.id
        assert loaded_logs[0].timestamp == log.timestamp
        assert loaded_logs[0].client_mac == log.client_mac
        assert loaded_logs[0].device_id == log.device_id
        assert loaded_logs[0].outcome == log.outcome
        assert loaded_logs[0].vlan_id == log.vlan_id


# ============================================================
# Property-Based Tests
# ============================================================

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Shared strategies
# ---------------------------------------------------------------------------

# Valid non-empty strings (no surrogate / null characters)
_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=50,
)

# Valid IPv4 addresses
_ipv4 = st.builds(
    lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
    st.integers(min_value=0, max_value=255),
)

# Datetime strategy (no timezone, microsecond precision)
_dt = st.datetimes(min_value=datetime(2000, 1, 1), max_value=datetime(2099, 12, 31))


def _device_group_st():
    """Strategy that generates a single DeviceGroup."""
    return st.builds(
        DeviceGroup,
        id=_text,
        name=_text,
        created_at=_dt,
        updated_at=_dt,
    )


def _device_st(group_id: str):
    """Strategy that generates a Device assigned to *group_id*."""
    return st.builds(
        Device,
        id=_text,
        ip_address=_ipv4,
        shared_secret=_text,
        device_group_id=st.just(group_id),
        created_at=_dt,
        updated_at=_dt,
    )


def _devices_and_groups_st():
    """
    Composite strategy that produces (devices, groups) where every device's
    device_group_id refers to one of the generated groups.
    """

    @st.composite
    def _build(draw):
        groups = draw(
            st.lists(_device_group_st(), min_size=1, max_size=5, unique_by=lambda g: g.id)
        )
        group_ids = [g.id for g in groups]
        devices = draw(
            st.lists(
                st.one_of(*[_device_st(gid) for gid in group_ids]),
                min_size=0,
                max_size=10,
                unique_by=lambda d: d.id,
            )
        )
        return devices, groups

    return _build()


# ---------------------------------------------------------------------------
# Property 39: Device Persistence Round-Trip
# ---------------------------------------------------------------------------


class TestPropertyDevicePersistenceRoundTrip:
    """
    **Validates: Requirements 7.1**

    Property 39: Device Persistence Round-Trip

    For any set of devices and device groups created in the system, after writing
    to persistent storage and reading back, the retrieved data SHALL be identical
    to the original data.
    """

    @settings(max_examples=50)
    @given(groups=st.lists(_device_group_st(), min_size=1, max_size=5, unique_by=lambda g: g.id))
    def test_device_groups_round_trip(self, groups):
        """
        Feature: simple-radius-server, Property 39: Device Persistence Round-Trip

        Device groups written to storage and read back are identical to the originals.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            devices_file = os.path.join(tmpdir, "devices.json")
            with patch("src.persistence.DEVICES_FILE", devices_file), \
                 patch("src.persistence.CLIENTS_FILE", os.path.join(tmpdir, "clients.json")), \
                 patch("src.persistence.POLICIES_FILE", os.path.join(tmpdir, "policies.json")), \
                 patch("src.persistence.LOGS_FILE", os.path.join(tmpdir, "logs.json")):

                DevicePersistence.save([], groups)
                _, loaded_groups = DevicePersistence.load()

        assert len(loaded_groups) == len(groups)
        loaded_by_id = {g.id: g for g in loaded_groups}
        for original in groups:
            loaded = loaded_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.name == original.name
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at

    @settings(max_examples=50)
    @given(data=_devices_and_groups_st())
    def test_devices_and_groups_round_trip(self, data):
        """
        Feature: simple-radius-server, Property 39: Device Persistence Round-Trip

        For any combination of devices and device groups, the full round-trip
        (save then load) produces data identical to the original.
        """
        devices, groups = data

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.persistence.DEVICES_FILE", os.path.join(tmpdir, "devices.json")), \
                 patch("src.persistence.CLIENTS_FILE", os.path.join(tmpdir, "clients.json")), \
                 patch("src.persistence.POLICIES_FILE", os.path.join(tmpdir, "policies.json")), \
                 patch("src.persistence.LOGS_FILE", os.path.join(tmpdir, "logs.json")):

                DevicePersistence.save(devices, groups)
                loaded_devices, loaded_groups = DevicePersistence.load()

        # --- groups round-trip ---
        assert len(loaded_groups) == len(groups)
        loaded_groups_by_id = {g.id: g for g in loaded_groups}
        for original in groups:
            loaded = loaded_groups_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.name == original.name
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at

        # --- devices round-trip ---
        assert len(loaded_devices) == len(devices)
        loaded_devices_by_id = {d.id: d for d in loaded_devices}
        for original in devices:
            loaded = loaded_devices_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.ip_address == original.ip_address
            assert loaded.shared_secret == original.shared_secret
            assert loaded.device_group_id == original.device_group_id
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at


# ---------------------------------------------------------------------------
# Shared strategies for clients, policies, logs
# ---------------------------------------------------------------------------

_mac_address = st.builds(
    lambda octets: ":".join(f"{b:02X}" for b in octets),
    st.lists(st.integers(min_value=0, max_value=255), min_size=6, max_size=6),
)

_vlan_id = st.integers(min_value=1, max_value=4094)

_policy_decision = st.sampled_from(list(PolicyDecision))

_auth_outcome = st.sampled_from(list(AuthenticationOutcome))


def _client_group_st():
    return st.builds(ClientGroup, id=_text, name=_text, created_at=_dt, updated_at=_dt)


def _client_st(group_id: str):
    return st.builds(
        Client,
        mac_address=_mac_address,
        client_group_id=st.just(group_id),
        created_at=_dt,
        updated_at=_dt,
    )


@st.composite
def _clients_and_groups_st(draw):
    groups = draw(
        st.lists(_client_group_st(), min_size=1, max_size=5, unique_by=lambda g: g.id)
    )
    group_ids = [g.id for g in groups]
    clients = draw(
        st.lists(
            st.one_of(*[_client_st(gid) for gid in group_ids]),
            min_size=0,
            max_size=10,
            unique_by=lambda c: c.mac_address,
        )
    )
    return clients, groups


def _mab_policy_st():
    return st.builds(
        MABPolicy,
        id=_text,
        client_group_id=_text,
        decision=_policy_decision,
        vlan_id=st.one_of(st.none(), _vlan_id),
        created_at=_dt,
        updated_at=_dt,
    )


def _auth_log_st():
    return st.builds(
        AuthenticationLog,
        id=_text,
        timestamp=_dt,
        client_mac=_mac_address,
        device_id=_text,
        outcome=_auth_outcome,
        vlan_id=st.one_of(st.none(), _vlan_id),
        created_at=_dt,
    )


# ---------------------------------------------------------------------------
# Property 40: Client Persistence Round-Trip
# ---------------------------------------------------------------------------


class TestPropertyClientPersistenceRoundTrip:
    """
    **Validates: Requirements 7.2**

    Property 40: Client Persistence Round-Trip

    For any set of clients and client groups created in the system, after writing
    to persistent storage and reading back, the retrieved data SHALL be identical
    to the original data.
    """

    @settings(max_examples=50)
    @given(data=_clients_and_groups_st())
    def test_clients_and_groups_round_trip(self, data):
        """
        Feature: simple-radius-server, Property 40: Client Persistence Round-Trip
        """
        clients, groups = data

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.persistence.DEVICES_FILE", os.path.join(tmpdir, "devices.json")), \
                 patch("src.persistence.CLIENTS_FILE", os.path.join(tmpdir, "clients.json")), \
                 patch("src.persistence.POLICIES_FILE", os.path.join(tmpdir, "policies.json")), \
                 patch("src.persistence.LOGS_FILE", os.path.join(tmpdir, "logs.json")):

                ClientPersistence.save(clients, groups)
                loaded_clients, loaded_groups = ClientPersistence.load()

        assert len(loaded_groups) == len(groups)
        loaded_groups_by_id = {g.id: g for g in loaded_groups}
        for original in groups:
            loaded = loaded_groups_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.name == original.name
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at

        assert len(loaded_clients) == len(clients)
        loaded_clients_by_mac = {c.mac_address: c for c in loaded_clients}
        for original in clients:
            loaded = loaded_clients_by_mac[original.mac_address]
            assert loaded.mac_address == original.mac_address
            assert loaded.client_group_id == original.client_group_id
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at


# ---------------------------------------------------------------------------
# Property 41: Policy Persistence Round-Trip
# ---------------------------------------------------------------------------


class TestPropertyPolicyPersistenceRoundTrip:
    """
    **Validates: Requirements 7.3**

    Property 41: Policy Persistence Round-Trip

    For any set of MAB_Policies created in the system, after writing to persistent
    storage and reading back, the retrieved data SHALL be identical to the original data.
    """

    @settings(max_examples=50)
    @given(policies=st.lists(_mab_policy_st(), min_size=0, max_size=10, unique_by=lambda p: p.id))
    def test_policies_round_trip(self, policies):
        """
        Feature: simple-radius-server, Property 41: Policy Persistence Round-Trip
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.persistence.DEVICES_FILE", os.path.join(tmpdir, "devices.json")), \
                 patch("src.persistence.CLIENTS_FILE", os.path.join(tmpdir, "clients.json")), \
                 patch("src.persistence.POLICIES_FILE", os.path.join(tmpdir, "policies.json")), \
                 patch("src.persistence.LOGS_FILE", os.path.join(tmpdir, "logs.json")):

                PolicyPersistence.save(policies)
                loaded_policies = PolicyPersistence.load()

        assert len(loaded_policies) == len(policies)
        loaded_by_id = {p.id: p for p in loaded_policies}
        for original in policies:
            loaded = loaded_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.client_group_id == original.client_group_id
            assert loaded.decision == original.decision
            assert loaded.vlan_id == original.vlan_id
            assert loaded.created_at == original.created_at
            assert loaded.updated_at == original.updated_at


# ---------------------------------------------------------------------------
# Property 42: Log Persistence Round-Trip
# ---------------------------------------------------------------------------


class TestPropertyLogPersistenceRoundTrip:
    """
    **Validates: Requirements 7.4**

    Property 42: Log Persistence Round-Trip

    For any set of Authentication_Log entries created in the system, after writing
    to persistent storage and reading back, the retrieved data SHALL be identical
    to the original data.
    """

    @settings(max_examples=50)
    @given(logs=st.lists(_auth_log_st(), min_size=0, max_size=10, unique_by=lambda l: l.id))
    def test_logs_round_trip(self, logs):
        """
        Feature: simple-radius-server, Property 42: Log Persistence Round-Trip
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("src.persistence.DEVICES_FILE", os.path.join(tmpdir, "devices.json")), \
                 patch("src.persistence.CLIENTS_FILE", os.path.join(tmpdir, "clients.json")), \
                 patch("src.persistence.POLICIES_FILE", os.path.join(tmpdir, "policies.json")), \
                 patch("src.persistence.LOGS_FILE", os.path.join(tmpdir, "logs.json")):

                LogPersistence.save(logs)
                loaded_logs = LogPersistence.load()

        assert len(loaded_logs) == len(logs)
        loaded_by_id = {l.id: l for l in loaded_logs}
        for original in logs:
            loaded = loaded_by_id[original.id]
            assert loaded.id == original.id
            assert loaded.timestamp == original.timestamp
            assert loaded.client_mac == original.client_mac
            assert loaded.device_id == original.device_id
            assert loaded.outcome == original.outcome
            assert loaded.vlan_id == original.vlan_id
            assert loaded.created_at == original.created_at
