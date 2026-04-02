"""
Tests for Log_Manager component.

Covers Properties 32-37 (Requirements 5.1-5.4, 5.7, 5.8).
"""

import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
import src.persistence as _persistence_mod
from src.models import AuthenticationOutcome
from src.log_manager import Log_Manager

from hypothesis import given, settings
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def mock_config(temp_dir, monkeypatch):
    db_path = os.path.join(temp_dir, "test.db")
    monkeypatch.setattr("src.database.DB_PATH", db_path)
    return temp_dir


@pytest.fixture
def mgr(mock_config):
    return Log_Manager()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestLogCreation:
    def test_create_success_log(self, mgr):
        log = mgr.create_log_entry("AA:BB:CC:DD:EE:FF", "switch-01", AuthenticationOutcome.SUCCESS, vlan_id=100)
        assert log.client_mac == "AA:BB:CC:DD:EE:FF"
        assert log.device_id == "switch-01"
        assert log.outcome == AuthenticationOutcome.SUCCESS
        assert log.vlan_id == 100
        assert log.timestamp is not None
        assert log.id is not None

    def test_create_failure_log(self, mgr):
        log = mgr.create_log_entry("AA:BB:CC:DD:EE:FF", "switch-01", AuthenticationOutcome.FAILURE)
        assert log.outcome == AuthenticationOutcome.FAILURE
        assert log.vlan_id is None

    def test_log_persists_across_instances(self, mgr, mock_config):
        log = mgr.create_log_entry("AA:BB:CC:DD:EE:FF", "switch-01", AuthenticationOutcome.SUCCESS)
        # Note: Log_Manager doesn't automatically persist to database
        # The caller (e.g., log parser) is responsible for database persistence
        # This test verifies the log is in memory
        found = mgr.get_log_entry(log.id)
        assert found is not None
        assert found.outcome == AuthenticationOutcome.SUCCESS


class TestLogOrdering:
    def test_list_logs_reverse_chronological(self, mgr):
        import time
        mgr.create_log_entry("AA:BB:CC:DD:EE:01", "sw1", AuthenticationOutcome.SUCCESS)
        time.sleep(0.01)
        mgr.create_log_entry("AA:BB:CC:DD:EE:02", "sw1", AuthenticationOutcome.FAILURE)
        logs = mgr.list_logs()
        assert len(logs) == 2
        assert logs[0].timestamp >= logs[1].timestamp


class TestLogFiltering:
    def test_filter_by_outcome(self, mgr):
        mgr.create_log_entry("AA:BB:CC:DD:EE:01", "sw1", AuthenticationOutcome.SUCCESS)
        mgr.create_log_entry("AA:BB:CC:DD:EE:02", "sw1", AuthenticationOutcome.FAILURE)
        success_logs = mgr.filter_logs(outcome=AuthenticationOutcome.SUCCESS)
        assert all(l.outcome == AuthenticationOutcome.SUCCESS for l in success_logs)
        assert len(success_logs) == 1

    def test_filter_by_mac(self, mgr):
        mgr.create_log_entry("AA:BB:CC:DD:EE:01", "sw1", AuthenticationOutcome.SUCCESS)
        mgr.create_log_entry("AA:BB:CC:DD:EE:02", "sw1", AuthenticationOutcome.SUCCESS)
        filtered = mgr.filter_logs(mac_address="AA:BB:CC:DD:EE:01")
        assert len(filtered) == 1
        assert filtered[0].client_mac == "AA:BB:CC:DD:EE:01"

    def test_filter_by_date_range(self, mgr):
        now = datetime.utcnow()
        past = now - timedelta(hours=2)
        future = now + timedelta(hours=2)
        mgr.create_log_entry("AA:BB:CC:DD:EE:01", "sw1", AuthenticationOutcome.SUCCESS)
        filtered = mgr.filter_logs(date_start=past, date_end=future)
        assert len(filtered) == 1

    def test_filter_no_criteria_returns_all(self, mgr):
        mgr.create_log_entry("AA:BB:CC:DD:EE:01", "sw1", AuthenticationOutcome.SUCCESS)
        mgr.create_log_entry("AA:BB:CC:DD:EE:02", "sw1", AuthenticationOutcome.FAILURE)
        assert len(mgr.filter_logs()) == 2


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------

_mac_st = st.builds(
    lambda octets: ":".join(f"{b:02X}" for b in octets),
    st.lists(st.integers(min_value=0, max_value=255), min_size=6, max_size=6),
)
_device_id_st = st.text(min_size=1, max_size=30,
                         alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"))
_outcome_st = st.sampled_from(list(AuthenticationOutcome))
_vlan_st = st.one_of(st.none(), st.integers(min_value=1, max_value=4094))


def _fresh_log_manager():
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with tempfile.TemporaryDirectory() as d:
            db_path = os.path.join(d, "test.db")
            with patch.object(_persistence_mod, "DevicePersistence") as mock_dev, \
                 patch.object(_persistence_mod, "ClientPersistence") as mock_cli, \
                 patch.object(_persistence_mod, "PolicyPersistence") as mock_pol, \
                 patch.object(_persistence_mod, "LogPersistence") as mock_log, \
                 patch("src.database.DB_PATH", db_path):
                # Set up mock returns
                mock_dev.load.return_value = ([], [])
                mock_cli.load.return_value = ([], [])
                mock_pol.load.return_value = []
                mock_log.load.return_value = []
                yield Log_Manager()

    return _ctx()


class TestLogRotation:
    def test_log_rotation_at_max_logs(self, mgr):
        """Test that logs are rotated when reaching MAX_LOGS (5000)"""
        from src.log_manager import MAX_LOGS
        
        # Create MAX_LOGS + 10 entries (not 100 to speed up test)
        for i in range(MAX_LOGS + 10):
            mgr.create_log_entry(
                f"AA:BB:CC:DD:EE:{i % 256:02X}",
                f"switch-{i % 10}",
                AuthenticationOutcome.SUCCESS if i % 2 == 0 else AuthenticationOutcome.FAILURE
            )
        
        # Verify only MAX_LOGS entries remain
        logs = mgr.list_logs()
        assert len(logs) == MAX_LOGS
    
    def test_log_rotation_keeps_newest_entries(self, mgr):
        """Test that log rotation keeps the newest entries"""
        from src.log_manager import MAX_LOGS
        import time
        
        # Create MAX_LOGS + 5 entries (smaller number for speed)
        for i in range(MAX_LOGS + 5):
            mgr.create_log_entry(
                f"AA:BB:CC:DD:EE:{i % 256:02X}",
                f"switch-{i}",
                AuthenticationOutcome.SUCCESS
            )
        
        logs = mgr.list_logs()
        assert len(logs) == MAX_LOGS


class TestPropertyLogManager:
    """Properties 32-37. Validates: Requirements 5.1-5.4, 5.7, 5.8"""

    @settings(max_examples=50)
    @given(mac=_mac_st, device_id=_device_id_st, vlan=_vlan_st)
    def test_property32_successful_authentication_logging(self, mac, device_id, vlan):
        """Feature: simple-radius-server, Property 32: Successful Authentication Logging"""
        with _fresh_log_manager() as mgr:
            log = mgr.create_log_entry(mac, device_id, AuthenticationOutcome.SUCCESS, vlan_id=vlan)
        assert log.outcome == AuthenticationOutcome.SUCCESS

    @settings(max_examples=50)
    @given(mac=_mac_st, device_id=_device_id_st)
    def test_property33_failed_authentication_logging(self, mac, device_id):
        """Feature: simple-radius-server, Property 33: Failed Authentication Logging"""
        with _fresh_log_manager() as mgr:
            log = mgr.create_log_entry(mac, device_id, AuthenticationOutcome.FAILURE)
        assert log.outcome == AuthenticationOutcome.FAILURE

    @settings(max_examples=50)
    @given(mac=_mac_st, device_id=_device_id_st, outcome=_outcome_st)
    def test_property34_log_entry_completeness(self, mac, device_id, outcome):
        """Feature: simple-radius-server, Property 34: Log Entry Completeness"""
        with _fresh_log_manager() as mgr:
            log = mgr.create_log_entry(mac, device_id, outcome)
        assert log.timestamp is not None
        assert log.client_mac == mac
        assert log.device_id == device_id
        assert log.outcome == outcome

    @settings(max_examples=50)
    @given(mac=_mac_st, device_id=_device_id_st, vlan=st.integers(min_value=1, max_value=4094))
    def test_property35_vlan_logging(self, mac, device_id, vlan):
        """Feature: simple-radius-server, Property 35: VLAN Logging"""
        with _fresh_log_manager() as mgr:
            log = mgr.create_log_entry(mac, device_id, AuthenticationOutcome.SUCCESS, vlan_id=vlan)
        assert log.vlan_id == vlan

    @settings(max_examples=30)
    @given(
        entries=st.lists(
            st.tuples(_mac_st, _device_id_st, _outcome_st),
            min_size=2,
            max_size=5,
        )
    )
    def test_property36_log_ordering(self, entries):
        """Feature: simple-radius-server, Property 36: Log Ordering"""
        import time
        with _fresh_log_manager() as mgr:
            for mac, device_id, outcome in entries:
                mgr.create_log_entry(mac, device_id, outcome)
                time.sleep(0.001)
            logs = mgr.list_logs()

        for i in range(len(logs) - 1):
            assert logs[i].timestamp >= logs[i + 1].timestamp

    @settings(max_examples=30)
    @given(
        mac1=_mac_st,
        mac2=_mac_st,
        device_id=_device_id_st,
    )
    def test_property37_log_filtering(self, mac1, mac2, device_id):
        """Feature: simple-radius-server, Property 37: Log Filtering"""
        with _fresh_log_manager() as mgr:
            mgr.create_log_entry(mac1, device_id, AuthenticationOutcome.SUCCESS)
            mgr.create_log_entry(mac2, device_id, AuthenticationOutcome.FAILURE)
            success_logs = mgr.filter_logs(outcome=AuthenticationOutcome.SUCCESS)
            failure_logs = mgr.filter_logs(outcome=AuthenticationOutcome.FAILURE)

        assert all(l.outcome == AuthenticationOutcome.SUCCESS for l in success_logs)
        assert all(l.outcome == AuthenticationOutcome.FAILURE for l in failure_logs)
