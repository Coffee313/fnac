"""
Integration tests for data persistence across server restarts.

Validates: Requirements 7.5
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import src.persistence as _persistence_mod
from src.client_manager import Client_Manager
from src.device_manager import Device_Manager
from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome, PolicyDecision
from src.policy_engine import Policy_Engine


@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def patched_paths(temp_dir, monkeypatch):
    monkeypatch.setattr("src.persistence.DEVICES_FILE", os.path.join(temp_dir, "devices.json"))
    monkeypatch.setattr("src.persistence.CLIENTS_FILE", os.path.join(temp_dir, "clients.json"))
    monkeypatch.setattr("src.persistence.POLICIES_FILE", os.path.join(temp_dir, "policies.json"))
    monkeypatch.setattr("src.persistence.LOGS_FILE", os.path.join(temp_dir, "logs.json"))
    return temp_dir


class TestPersistenceAcrossRestarts:
    """
    Validates: Requirements 7.5

    Simulates a server restart by creating new manager instances that load
    from the same persisted files.
    """

    def test_devices_survive_restart(self, patched_paths):
        """Devices and groups created before restart are available after restart."""
        dm1 = Device_Manager()
        dm1.create_device_group("g1", "Access Layer")
        dm1.create_device("sw1", "192.168.1.1", "secret", "g1")

        # Simulate restart
        dm2 = Device_Manager()
        assert dm2.get_device("sw1") is not None
        assert dm2.get_device("sw1").ip_address == "192.168.1.1"
        assert dm2.get_device_group("g1") is not None

    def test_clients_survive_restart(self, patched_paths):
        """Clients and groups created before restart are available after restart."""
        cm1 = Client_Manager()
        cm1.create_client_group("cg1", "Printers")
        cm1.create_client("AA:BB:CC:DD:EE:FF", "cg1")

        cm2 = Client_Manager()
        assert cm2.get_client("AA:BB:CC:DD:EE:FF") is not None
        assert cm2.get_client_group("cg1") is not None

    def test_policies_survive_restart(self, patched_paths):
        """Policies created before restart are available after restart."""
        pe1 = Policy_Engine()
        pe1.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=100)

        pe2 = Policy_Engine()
        decision, vlan, policy_name = pe2.evaluate_policy("cg1")
        assert decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert vlan == 100
        assert policy_name == "p1"

    def test_logs_survive_restart(self, patched_paths):
        """Authentication logs created before restart are available after restart."""
        lm1 = Log_Manager()
        log = lm1.create_log_entry("AA:BB:CC:DD:EE:FF", "sw1", AuthenticationOutcome.SUCCESS, vlan_id=42)

        lm2 = Log_Manager()
        found = lm2.get_log_entry(log.id)
        assert found is not None
        assert found.outcome == AuthenticationOutcome.SUCCESS
        assert found.vlan_id == 42

    def test_full_state_survives_restart(self, patched_paths):
        """Complete system state survives a simulated restart."""
        # Setup
        dm1 = Device_Manager()
        cm1 = Client_Manager()
        pe1 = Policy_Engine()
        lm1 = Log_Manager()

        dm1.create_device_group("dg1", "Access")
        dm1.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm1.create_client_group("cg1", "Laptops")
        cm1.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe1.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=10)
        lm1.create_log_entry("AA:BB:CC:DD:EE:FF", "sw1", AuthenticationOutcome.SUCCESS, vlan_id=10)

        # Simulate restart
        dm2 = Device_Manager()
        cm2 = Client_Manager()
        pe2 = Policy_Engine()
        lm2 = Log_Manager()

        assert dm2.get_device("sw1").device_group_id == "dg1"
        assert cm2.get_client("AA:BB:CC:DD:EE:FF").client_group_id == "cg1"
        decision, vlan, policy_name = pe2.evaluate_policy("cg1")
        assert decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert vlan == 10
        assert policy_name == "p1"
        logs = lm2.list_logs()
        assert len(logs) == 1
        assert logs[0].outcome == AuthenticationOutcome.SUCCESS

    def test_data_integrity_after_restart(self, patched_paths):
        """Data integrity is maintained: referential relationships are preserved."""
        dm1 = Device_Manager()
        cm1 = Client_Manager()

        dm1.create_device_group("dg1", "Group A")
        dm1.create_device_group("dg2", "Group B")
        dm1.create_device("sw1", "10.0.0.1", "s1", "dg1")
        dm1.create_device("sw2", "10.0.0.2", "s2", "dg2")
        cm1.create_client_group("cg1", "Printers")
        cm1.create_client("AA:BB:CC:DD:EE:01", "cg1")
        cm1.create_client("AA:BB:CC:DD:EE:02", "cg1")

        # Simulate restart
        dm2 = Device_Manager()
        cm2 = Client_Manager()

        assert len(dm2.list_devices()) == 2
        assert len(dm2.list_device_groups()) == 2
        assert len(cm2.list_clients()) == 2
        assert len(cm2.list_client_groups()) == 1

        # Verify referential integrity
        for device in dm2.list_devices():
            assert dm2.get_device_group(device.device_group_id) is not None
        for client in cm2.list_clients():
            assert cm2.get_client_group(client.client_group_id) is not None
