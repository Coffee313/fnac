"""
Tests for the persistence layer.

Tests database persistence for devices, clients, policies, and logs.
"""

import os
import tempfile
from datetime import datetime

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
    ClientPersistence,
    DevicePersistence,
    LogPersistence,
    PolicyPersistence,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def mock_db_device(temp_dir, monkeypatch):
    """Mock database path for device tests."""
    db_path = os.path.join(temp_dir, "test_device.db")
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    # Force reimport to pick up new DB_PATH
    import importlib
    import src.database
    importlib.reload(src.database)
    yield db_path


@pytest.fixture
def mock_db_client(temp_dir, monkeypatch):
    """Mock database path for client tests."""
    db_path = os.path.join(temp_dir, "test_client.db")
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    import importlib
    import src.database
    importlib.reload(src.database)
    yield db_path


@pytest.fixture
def mock_db_policy(temp_dir, monkeypatch):
    """Mock database path for policy tests."""
    db_path = os.path.join(temp_dir, "test_policy.db")
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    import importlib
    import src.database
    importlib.reload(src.database)
    yield db_path


@pytest.fixture
def mock_db_log(temp_dir, monkeypatch):
    """Mock database path for log tests."""
    db_path = os.path.join(temp_dir, "test_log.db")
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    import importlib
    import src.database
    importlib.reload(src.database)
    yield db_path


class TestDevicePersistence:
    """Tests for device persistence."""

    def test_save_and_load_devices(self, mock_db_device):
        """Test saving and loading devices."""
        group = DeviceGroup(name="group1", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        device = Device(
            name="device1",
            ip_address="192.168.1.1",
            shared_secret="secret",
            device_group_name="group1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        DevicePersistence.save([device], [group])
        loaded_devices, loaded_groups = DevicePersistence.load()
        
        assert len(loaded_devices) == 1
        assert loaded_devices[0].name == "device1"
        assert len(loaded_groups) == 1
        assert loaded_groups[0].name == "group1"


class TestClientPersistence:
    """Tests for client persistence."""

    def test_save_and_load_clients(self, mock_db_client):
        """Test saving and loading clients."""
        group = ClientGroup(name="group1", created_at=datetime.utcnow(), updated_at=datetime.utcnow())
        client = Client(
            mac_address="AA:BB:CC:DD:EE:FF",
            name="client1",
            client_group_name="group1",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        ClientPersistence.save([client], [group])
        loaded_clients, loaded_groups = ClientPersistence.load()
        
        assert len(loaded_clients) == 1
        # MAC addresses are normalized to lowercase
        assert loaded_clients[0].mac_address == "aa:bb:cc:dd:ee:ff"
        assert len(loaded_groups) == 1
        assert loaded_groups[0].name == "group1"


class TestPolicyPersistence:
    """Tests for policy persistence."""

    def test_save_and_load_policies(self, mock_db_policy):
        """Test saving and loading policies."""
        policy = MABPolicy(
            name="policy1",
            client_group_name="group1",
            decision=PolicyDecision.ACCEPT_WITH_VLAN,
            vlan_id=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        PolicyPersistence.save([policy])
        loaded_policies = PolicyPersistence.load()
        
        assert len(loaded_policies) == 1
        assert loaded_policies[0].name == "policy1"
        assert loaded_policies[0].vlan_id == 100


class TestLogPersistence:
    """Tests for log persistence."""

    def test_save_and_load_logs(self, mock_db_log):
        """Test saving and loading logs."""
        log = AuthenticationLog(
            id="log1",
            timestamp=datetime.utcnow(),
            client_mac="AA:BB:CC:DD:EE:FF",
            device_id="device1",
            outcome=AuthenticationOutcome.SUCCESS,
            vlan_id=100,
            policy_name="policy1",
            policy_decision="accept_with_vlan",
            created_at=datetime.utcnow(),
        )
        
        LogPersistence.save([log])
        loaded_logs = LogPersistence.load()
        
        assert len(loaded_logs) == 1
        assert loaded_logs[0].client_mac == "AA:BB:CC:DD:EE:FF"
        assert loaded_logs[0].outcome == AuthenticationOutcome.SUCCESS
