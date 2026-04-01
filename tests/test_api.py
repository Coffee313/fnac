"""
Tests for Flask REST API configuration interface.

Covers Property 44 (Requirements 8.5, 8.6) and basic API functionality.
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import src.persistence as _persistence_mod
from src.api import create_app
from src.client_manager import Client_Manager
from src.device_manager import Device_Manager
from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome, PolicyDecision
from src.policy_engine import Policy_Engine

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
    monkeypatch.setattr("src.persistence.DEVICES_FILE", os.path.join(temp_dir, "devices.json"))
    monkeypatch.setattr("src.persistence.CLIENTS_FILE", os.path.join(temp_dir, "clients.json"))
    monkeypatch.setattr("src.persistence.POLICIES_FILE", os.path.join(temp_dir, "policies.json"))
    monkeypatch.setattr("src.persistence.LOGS_FILE", os.path.join(temp_dir, "logs.json"))
    return temp_dir


@pytest.fixture
def client(mock_config):
    dm = Device_Manager()
    cm = Client_Manager()
    pe = Policy_Engine()
    lm = Log_Manager()
    app = create_app(dm, cm, pe, lm)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, dm, cm, pe, lm


# ---------------------------------------------------------------------------
# Device API tests
# ---------------------------------------------------------------------------

class TestDeviceAPI:
    def test_list_devices_empty(self, client):
        c, *_ = client
        resp = c.get("/api/devices")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_create_device(self, client):
        c, dm, *_ = client
        dm.create_device_group("g1", "Group")
        resp = c.post("/api/devices", json={
            "id": "sw1", "ip_address": "10.0.0.1",
            "shared_secret": "secret", "device_group_id": "g1"
        })
        assert resp.status_code == 201
        assert resp.get_json()["id"] == "sw1"

    def test_create_device_missing_field_returns_400(self, client):
        c, *_ = client
        resp = c.post("/api/devices", json={"id": "sw1"})
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_device_invalid_ip_returns_400(self, client):
        c, dm, *_ = client
        dm.create_device_group("g1", "Group")
        resp = c.post("/api/devices", json={
            "id": "sw1", "ip_address": "not-an-ip",
            "shared_secret": "secret", "device_group_id": "g1"
        })
        assert resp.status_code == 400

    def test_delete_device(self, client):
        c, dm, *_ = client
        dm.create_device_group("g1", "Group")
        dm.create_device("sw1", "10.0.0.1", "secret", "g1")
        resp = c.delete("/api/devices/sw1")
        assert resp.status_code == 204

    def test_delete_nonexistent_device_returns_404(self, client):
        c, *_ = client
        resp = c.delete("/api/devices/nonexistent")
        assert resp.status_code == 404


class TestClientAPI:
    def test_create_client(self, client):
        c, _, cm, *_ = client
        cm.create_client_group("cg1", "Group")
        resp = c.post("/api/clients", json={
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "client_group_id": "cg1"
        })
        assert resp.status_code == 201

    def test_create_client_invalid_mac_returns_400(self, client):
        c, _, cm, *_ = client
        cm.create_client_group("cg1", "Group")
        resp = c.post("/api/clients", json={
            "mac_address": "not-a-mac",
            "client_group_id": "cg1"
        })
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_create_client_missing_field_returns_400(self, client):
        c, *_ = client
        resp = c.post("/api/clients", json={"mac_address": "AA:BB:CC:DD:EE:FF"})
        assert resp.status_code == 400


class TestPolicyAPI:
    def test_create_policy(self, client):
        c, _, _, pe, _ = client
        resp = c.post("/api/policies", json={
            "id": "p1", "client_group_id": "cg1",
            "decision": "reject"
        })
        assert resp.status_code == 201

    def test_create_policy_invalid_decision_returns_400(self, client):
        c, *_ = client
        resp = c.post("/api/policies", json={
            "id": "p1", "client_group_id": "cg1",
            "decision": "invalid_decision"
        })
        assert resp.status_code == 400

    def test_create_policy_invalid_vlan_returns_400(self, client):
        c, *_ = client
        resp = c.post("/api/policies", json={
            "id": "p1", "client_group_id": "cg1",
            "decision": "accept_with_vlan", "vlan_id": 9999
        })
        assert resp.status_code == 400

    def test_delete_nonexistent_policy_returns_404(self, client):
        c, *_ = client
        resp = c.delete("/api/policies/nonexistent")
        assert resp.status_code == 404


class TestLogAPI:
    def test_list_logs_empty(self, client):
        c, *_ = client
        resp = c.get("/api/logs")
        assert resp.status_code == 200
        assert resp.get_json() == []

    def test_list_logs_with_outcome_filter(self, client):
        c, _, _, _, lm = client
        lm.create_log_entry("AA:BB:CC:DD:EE:FF", "sw1", AuthenticationOutcome.SUCCESS)
        lm.create_log_entry("AA:BB:CC:DD:EE:FE", "sw1", AuthenticationOutcome.FAILURE)
        resp = c.get("/api/logs?outcome=success")
        assert resp.status_code == 200
        logs = resp.get_json()
        assert len(logs) == 1
        assert logs[0]["outcome"] == "success"

    def test_list_logs_invalid_outcome_returns_400(self, client):
        c, *_ = client
        resp = c.get("/api/logs?outcome=invalid")
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Property 44: Configuration Validation
# ---------------------------------------------------------------------------

_invalid_mac_st = st.one_of(
    st.just(""),
    st.just("AA:BB:CC:DD:EE"),
    st.just("AA-BB-CC-DD-EE-FF"),
    st.just("AABBCCDDEEFF"),
    st.just("ZZ:BB:CC:DD:EE:FF"),
)

_invalid_vlan_st = st.one_of(
    st.just(0),
    st.just(4095),
    st.just(-1),
    st.just(99999),
)

_invalid_decision_st = st.text(min_size=1, max_size=20).filter(
    lambda s: s not in ("accept_with_vlan", "accept_without_vlan", "reject")
)


def _fresh_api_client():
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with tempfile.TemporaryDirectory() as d:
            with patch.object(_persistence_mod, "DEVICES_FILE", os.path.join(d, "devices.json")), \
                 patch.object(_persistence_mod, "CLIENTS_FILE", os.path.join(d, "clients.json")), \
                 patch.object(_persistence_mod, "POLICIES_FILE", os.path.join(d, "policies.json")), \
                 patch.object(_persistence_mod, "LOGS_FILE", os.path.join(d, "logs.json")):
                dm = Device_Manager()
                cm = Client_Manager()
                pe = Policy_Engine()
                lm = Log_Manager()
                app = create_app(dm, cm, pe, lm)
                app.config["TESTING"] = True
                with app.test_client() as c:
                    yield c, dm, cm, pe, lm

    return _ctx()


class TestPropertyConfigurationValidation:
    """
    Property 44: Configuration Validation
    Validates: Requirements 8.5, 8.6
    """

    @settings(max_examples=30)
    @given(invalid_mac=_invalid_mac_st)
    def test_invalid_mac_rejected_with_error_message(self, invalid_mac):
        """
        Feature: simple-radius-server, Property 44: Configuration Validation

        Invalid MAC address format SHALL be rejected with a descriptive error.
        """
        with _fresh_api_client() as (c, dm, cm, pe, lm):
            cm.create_client_group("cg1", "Group")
            resp = c.post("/api/clients", json={
                "mac_address": invalid_mac,
                "client_group_id": "cg1"
            })
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body
        assert len(body["error"]) > 0

    @settings(max_examples=20)
    @given(invalid_vlan=_invalid_vlan_st)
    def test_invalid_vlan_rejected_with_error_message(self, invalid_vlan):
        """
        Feature: simple-radius-server, Property 44: Configuration Validation

        VLAN ID outside 1-4094 SHALL be rejected with a descriptive error.
        """
        with _fresh_api_client() as (c, *_):
            resp = c.post("/api/policies", json={
                "id": "p1", "client_group_id": "cg1",
                "decision": "accept_with_vlan", "vlan_id": invalid_vlan
            })
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body

    @settings(max_examples=20)
    @given(invalid_decision=_invalid_decision_st)
    def test_invalid_decision_rejected_with_error_message(self, invalid_decision):
        """
        Feature: simple-radius-server, Property 44: Configuration Validation

        Invalid policy decision values SHALL be rejected with a descriptive error.
        """
        with _fresh_api_client() as (c, *_):
            resp = c.post("/api/policies", json={
                "id": "p1", "client_group_id": "cg1",
                "decision": invalid_decision
            })
        assert resp.status_code == 400
        body = resp.get_json()
        assert "error" in body

    @settings(max_examples=20)
    @given(
        missing_field=st.sampled_from(["id", "ip_address", "shared_secret", "device_group_id"])
    )
    def test_missing_required_fields_rejected(self, missing_field):
        """
        Feature: simple-radius-server, Property 44: Configuration Validation

        Missing required fields SHALL be rejected with a descriptive error.
        """
        full_body = {
            "id": "sw1", "ip_address": "10.0.0.1",
            "shared_secret": "secret", "device_group_id": "g1"
        }
        body = {k: v for k, v in full_body.items() if k != missing_field}
        with _fresh_api_client() as (c, dm, *_):
            dm.create_device_group("g1", "Group")
            resp = c.post("/api/devices", json=body)
        assert resp.status_code == 400
        assert "error" in resp.get_json()
