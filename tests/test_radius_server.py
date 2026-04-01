"""
Tests for RADIUS protocol handler and RADIUS_Server authentication flow.

Covers Properties 23-31, 38 (Requirements 4.1-4.10, 6.3).
"""

import os
import struct
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import src.persistence as _persistence_mod
from src.client_manager import Client_Manager
from src.device_manager import Device_Manager
from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome, PolicyDecision
from src.policy_engine import Policy_Engine
from src.radius_protocol import (
    CODE_ACCESS_ACCEPT,
    CODE_ACCESS_REJECT,
    ATTR_TUNNEL_PRIVATE_GROUP_ID,
    ATTR_TUNNEL_TYPE,
    ATTR_USER_NAME,
    RADIUSParseError,
    build_access_accept,
    build_access_reject,
    build_packet,
    extract_mac_from_username,
    parse_packet,
    RADIUSAttribute,
    RADIUSPacket,
)
from src.radius_server import RADIUS_Server

from hypothesis import given, settings, assume
from hypothesis import strategies as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_access_request(
    identifier: int = 1,
    username: str = "AA:BB:CC:DD:EE:FF",
    authenticator: bytes = b"\x00" * 16,
) -> bytes:
    """Build a minimal Access-Request packet."""
    username_bytes = username.encode("utf-8")
    attr = bytes([ATTR_USER_NAME, len(username_bytes) + 2]) + username_bytes
    length = 20 + len(attr)
    header = struct.pack("!BBH", 1, identifier, length)
    return header + authenticator + attr


def _make_server(temp_dir: str):
    """Create a RADIUS_Server with all managers backed by temp_dir."""
    with patch.object(_persistence_mod, "DEVICES_FILE", os.path.join(temp_dir, "devices.json")), \
         patch.object(_persistence_mod, "CLIENTS_FILE", os.path.join(temp_dir, "clients.json")), \
         patch.object(_persistence_mod, "POLICIES_FILE", os.path.join(temp_dir, "policies.json")), \
         patch.object(_persistence_mod, "LOGS_FILE", os.path.join(temp_dir, "logs.json")):
        dm = Device_Manager()
        cm = Client_Manager()
        pe = Policy_Engine()
        lm = Log_Manager()
    return dm, cm, pe, lm, RADIUS_Server(dm, cm, pe, lm)


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
def components(mock_config):
    dm = Device_Manager()
    cm = Client_Manager()
    pe = Policy_Engine()
    lm = Log_Manager()
    server = RADIUS_Server(dm, cm, pe, lm)
    return dm, cm, pe, lm, server


# ---------------------------------------------------------------------------
# Unit tests – RADIUS protocol
# ---------------------------------------------------------------------------

class TestRADIUSProtocol:
    def test_parse_valid_access_request(self):
        data = _make_access_request()
        packet = parse_packet(data)
        assert packet.code == 1
        assert packet.identifier == 1

    def test_parse_too_short_raises_error(self):
        with pytest.raises(RADIUSParseError):
            parse_packet(b"\x01\x01\x00\x14")  # only 4 bytes

    def test_parse_invalid_length_raises_error(self):
        data = _make_access_request()
        # Corrupt the length field to be too small
        bad = data[:2] + struct.pack("!H", 5) + data[4:]
        with pytest.raises(RADIUSParseError):
            parse_packet(bad)

    def test_extract_mac_from_username(self):
        data = _make_access_request(username="aabbccddeeff")
        packet = parse_packet(data)
        mac = extract_mac_from_username(packet)
        assert mac == "AA:BB:CC:DD:EE:FF"

    def test_extract_mac_colon_format(self):
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        packet = parse_packet(data)
        mac = extract_mac_from_username(packet)
        assert mac == "AA:BB:CC:DD:EE:FF"

    def test_build_access_accept_no_vlan(self):
        req_data = _make_access_request()
        req = parse_packet(req_data)
        resp = build_access_accept(req, "secret")
        resp_packet = parse_packet(resp)
        assert resp_packet.code == CODE_ACCESS_ACCEPT

    def test_build_access_accept_with_vlan(self):
        req_data = _make_access_request()
        req = parse_packet(req_data)
        resp = build_access_accept(req, "secret", vlan_id=100)
        resp_packet = parse_packet(resp)
        assert resp_packet.code == CODE_ACCESS_ACCEPT
        vlan_attr = resp_packet.get_attribute(ATTR_TUNNEL_PRIVATE_GROUP_ID)
        assert vlan_attr == b"100"

    def test_build_access_reject(self):
        req_data = _make_access_request()
        req = parse_packet(req_data)
        resp = build_access_reject(req, "secret")
        resp_packet = parse_packet(resp)
        assert resp_packet.code == CODE_ACCESS_REJECT

    def test_rfc2865_response_has_20_byte_header(self):
        req_data = _make_access_request()
        req = parse_packet(req_data)
        resp = build_access_reject(req, "secret")
        assert len(resp) >= 20
        # Length field matches actual length
        _, _, length = struct.unpack("!BBH", resp[:4])
        assert length == len(resp)


# ---------------------------------------------------------------------------
# Unit tests – RADIUS_Server authentication flow
# ---------------------------------------------------------------------------

class TestRADIUSServerFlow:
    def test_unregistered_device_drops_packet(self, components):
        dm, cm, pe, lm, server = components
        data = _make_access_request()
        response = server.handle_request(data, "10.0.0.99")
        assert response == b""

    def test_registered_device_unknown_client_returns_reject(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("g1", "Group")
        dm.create_device("sw1", "10.0.0.1", "secret", "g1")
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        response = server.handle_request(data, "10.0.0.1")
        resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    def test_known_client_reject_policy_returns_reject(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe.create_policy("p1", "cg1", PolicyDecision.REJECT)
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        response = server.handle_request(data, "10.0.0.1")
        resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    def test_known_client_accept_without_vlan(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        response = server.handle_request(data, "10.0.0.1")
        resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_ACCEPT
        assert resp_packet.get_attribute(ATTR_TUNNEL_PRIVATE_GROUP_ID) is None

    def test_known_client_accept_with_vlan(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=42)
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        response = server.handle_request(data, "10.0.0.1")
        resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_ACCEPT
        assert resp_packet.get_attribute(ATTR_TUNNEL_PRIVATE_GROUP_ID) == b"42"

    def test_missing_policy_returns_reject(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        # No policy created
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        response = server.handle_request(data, "10.0.0.1")
        resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    def test_successful_auth_creates_success_log(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        server.handle_request(data, "10.0.0.1")
        logs = lm.list_logs()
        assert any(l.outcome == AuthenticationOutcome.SUCCESS for l in logs)

    def test_failed_auth_creates_failure_log(self, components):
        dm, cm, pe, lm, server = components
        dm.create_device_group("dg1", "DG")
        dm.create_device("sw1", "10.0.0.1", "secret", "dg1")
        cm.create_client_group("cg1", "CG")
        cm.create_client("AA:BB:CC:DD:EE:FF", "cg1")
        pe.create_policy("p1", "cg1", PolicyDecision.REJECT)
        data = _make_access_request(username="AA:BB:CC:DD:EE:FF")
        server.handle_request(data, "10.0.0.1")
        logs = lm.list_logs()
        assert any(l.outcome == AuthenticationOutcome.FAILURE for l in logs)

    def test_malformed_packet_returns_empty(self, components):
        _, _, _, _, server = components
        response = server.handle_request(b"\x01\x01\x00", "10.0.0.1")
        assert response == b""


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------

_mac_st = st.builds(
    lambda octets: ":".join(f"{b:02X}" for b in octets),
    st.lists(st.integers(min_value=0, max_value=255), min_size=6, max_size=6),
)
_ip_st = st.builds(
    lambda a, b, c, d: f"{a}.{b}.{c}.{d}",
    st.integers(0, 255), st.integers(0, 255),
    st.integers(0, 255), st.integers(0, 255),
)
_secret_st = st.text(min_size=1, max_size=30,
                     alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"))
_vlan_st = st.integers(min_value=1, max_value=4094)
_id_st = st.text(min_size=1, max_size=20,
                 alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"))


def _fresh_server():
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
                yield dm, cm, pe, lm, RADIUS_Server(dm, cm, pe, lm)

    return _ctx()


class TestPropertyRADIUSServer:
    """Properties 23-31, 38. Validates: Requirements 4.1-4.10, 6.3"""

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property23_unregistered_device_rejected(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 23: RADIUS Request Device Verification"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
        assert response == b""

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property24_mac_extraction_from_request(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 24: MAC Address Extraction from RADIUS Request"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_ACCEPT

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property26_unknown_client_rejection(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 26: Unknown Client Rejection"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            # No client registered
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st, vlan=_vlan_st)
    def test_property28_accept_with_vlan_response(self, ip, secret, mac, vlan):
        """Feature: simple-radius-server, Property 28: Accept with VLAN Response"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=vlan)
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_ACCEPT
        assert resp_packet.get_attribute(ATTR_TUNNEL_PRIVATE_GROUP_ID) == str(vlan).encode("ascii")

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property29_accept_without_vlan_response(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 29: Accept without VLAN Response"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_ACCEPT
        assert resp_packet.get_attribute(ATTR_TUNNEL_PRIVATE_GROUP_ID) is None

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property30_reject_response(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 30: Reject Response"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            pe.create_policy("p1", "cg1", PolicyDecision.REJECT)
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property31_missing_policy_default_rejection(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 31: Missing Policy Default Rejection"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            # No policy
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)
            resp_packet = parse_packet(response)
        assert resp_packet.code == CODE_ACCESS_REJECT

    @settings(max_examples=30)
    @given(ip=_ip_st, secret=_secret_st, mac=_mac_st)
    def test_property38_rfc2865_protocol_compliance(self, ip, secret, mac):
        """Feature: simple-radius-server, Property 38: RFC 2865 Protocol Compliance"""
        with _fresh_server() as (dm, cm, pe, lm, server):
            dm.create_device_group("dg1", "DG")
            dm.create_device("sw1", ip, secret, "dg1")
            cm.create_client_group("cg1", "CG")
            cm.create_client(mac, "cg1")
            pe.create_policy("p1", "cg1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
            data = _make_access_request(username=mac)
            response = server.handle_request(data, ip)

        # Must be parseable and have valid code
        resp_packet = parse_packet(response)
        assert resp_packet.code in (CODE_ACCESS_ACCEPT, CODE_ACCESS_REJECT)
        # Length field must match actual length
        _, _, length = struct.unpack("!BBH", response[:4])
        assert length == len(response)
        # Authenticator must be 16 bytes
        assert len(resp_packet.authenticator) == 16
