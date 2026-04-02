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
from src.database import Database

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
def client(temp_dir, monkeypatch):
    """Create a fresh test client with isolated database for each test."""
    # Delete the default fnac.db if it exists to avoid cross-test contamination
    if os.path.exists("fnac.db"):
        os.remove("fnac.db")
    
    db_path = os.path.join(temp_dir, "fnac_test.db")
    
    # Patch BEFORE creating managers
    from src import database
    monkeypatch.setattr(database, "DB_PATH", db_path)
    
    # Now create fresh managers - they will use the patched DB_PATH
    dm = Device_Manager()
    cm = Client_Manager()
    pe = Policy_Engine()
    lm = Log_Manager()
    app = create_app(dm, cm, pe, lm)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c, dm, cm, pe, lm


@pytest.fixture
def mock_config(temp_dir, monkeypatch):
    """Legacy fixture for compatibility."""
    db_path = os.path.join(temp_dir, "fnac.db")
    from src import database
    monkeypatch.setattr(database, "DB_PATH", db_path)
    return temp_dir


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
            db_path = os.path.join(d, "fnac.db")
            with patch("src.database.DB_PATH", db_path):
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



# ---------------------------------------------------------------------------
# CSV Import/Export Tests
# ---------------------------------------------------------------------------

class TestCSVImportExport:
    """Tests for CSV import/export functionality for bulk client management."""

    def test_download_csv_template(self, client):
        """Test downloading CSV template."""
        c, *_ = client
        resp = c.get("/api/clients/csv-template")
        assert resp.status_code == 200
        assert resp.headers["Content-Type"] == "text/csv"
        assert "MAC Address" in resp.data.decode()
        assert "Client Name" in resp.data.decode()
        assert "Client Group" in resp.data.decode()

    def test_import_csv_basic(self, client):
        """Test basic CSV import with valid data."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        csv_content = "MAC Address,Client Name,Client Group\naa:bb:cc:dd:ee:ff,Client1,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["status"] == "success"
        assert result["results"]["imported"] == 1
        assert result["results"]["failed"] == 0

    def test_import_csv_duplicate_mac_prevention(self, client):
        """Test that duplicate MAC addresses are updated during import."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # Create an existing client
        cm.create_client("aa:bb:cc:dd:ee:ff", "Group1", name="Existing")
        
        # Try to import CSV with duplicate MAC but different name/group
        csv_content = "MAC Address,Client Name,Client Group\naa:bb:cc:dd:ee:ff,UpdatedName,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["updated"] == 1
        assert result["results"]["imported"] == 0
        assert result["results"]["failed"] == 0
        
        # Verify the client was updated
        updated_client = cm.get_client("aa:bb:cc:dd:ee:ff")
        assert updated_client.name == "UpdatedName"

    def test_import_csv_case_insensitive_duplicate_detection(self, client):
        """Test that duplicate MAC detection is case-insensitive and updates the client."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # Create client with lowercase MAC
        cm.create_client("aa:bb:cc:dd:ee:ff", "Group1", name="Original")
        
        # Try to import with uppercase MAC
        csv_content = "MAC Address,Client Name,Client Group\nAA:BB:CC:DD:EE:FF,Updated,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["updated"] == 1
        assert result["results"]["imported"] == 0

    def test_import_csv_mixed_results(self, client):
        """Test CSV import with mix of new and existing clients."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # Create one existing client
        cm.create_client("aa:bb:cc:dd:ee:ff", "Group1", name="Existing")
        
        # Import CSV with 1 existing (to update) and 2 new clients
        csv_content = """MAC Address,Client Name,Client Group
aa:bb:cc:dd:ee:ff,Updated,Group1
11:22:33:44:55:66,New1,Group1
22:33:44:55:66:77,New2,Group1
"""
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["imported"] == 2
        assert result["results"]["updated"] == 1
        assert result["results"]["failed"] == 0

    def test_import_csv_semicolon_delimiter(self, client):
        """Test CSV import with semicolon delimiter (Excel format)."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with semicolon delimiter
        csv_content = "MAC Address;Client Name;Client Group\naa:bb:cc:dd:ee:ff;Client1;Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["imported"] == 1

    def test_import_csv_tab_delimiter(self, client):
        """Test CSV import with tab delimiter."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with tab delimiter
        csv_content = "MAC Address\tClient Name\tClient Group\naa:bb:cc:dd:ee:ff\tClient1\tGroup1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["imported"] == 1

    def test_import_csv_case_insensitive_column_matching(self, client):
        """Test that column names are matched case-insensitively."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with different case column names
        csv_content = "mac address,client name,client group\naa:bb:cc:dd:ee:ff,Client1,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["imported"] == 1

    def test_import_csv_missing_mac_column(self, client):
        """Test that import fails if MAC Address column is missing."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV without MAC Address column
        csv_content = "Client Name,Client Group\nClient1,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 400
        result = resp.get_json()
        assert "error" in result

    def test_import_csv_missing_group_column(self, client):
        """Test that rows without Client Group are marked as failed."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with missing group in one row
        csv_content = "MAC Address,Client Name,Client Group\naa:bb:cc:dd:ee:ff,Client1,\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["failed"] == 1
        assert result["results"]["imported"] == 0

    def test_import_csv_missing_mac_in_row(self, client):
        """Test that rows without MAC Address are marked as failed."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with missing MAC in one row
        csv_content = "MAC Address,Client Name,Client Group\n,Client1,Group1\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["failed"] == 1
        assert result["results"]["imported"] == 0

    def test_import_csv_no_file_provided(self, client):
        """Test that import fails if no file is provided."""
        c, *_ = client
        resp = c.post("/api/clients/csv-import", data={}, content_type='multipart/form-data')
        assert resp.status_code == 400
        result = resp.get_json()
        assert "error" in result

    def test_import_csv_wrong_file_type(self, client):
        """Test that import fails if file is not CSV."""
        c, *_ = client
        from io import BytesIO
        data = {
            'file': (BytesIO(b'{"test": "data"}'), 'test.json')
        }
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 400
        result = resp.get_json()
        assert "error" in result

    def test_import_csv_multiple_formats(self, client):
        """Test CSV import with various MAC address formats."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        
        # CSV with different MAC formats
        csv_content = """MAC Address,Client Name,Client Group
aa:bb:cc:dd:ee:ff,Client1,Group1
aa-bb-cc-dd-ee-fe,Client2,Group1
aa.bb.cc.dd.ee.fd,Client3,Group1
"""
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        # All three should be imported (different MACs)
        assert result["results"]["imported"] == 3


    def test_import_csv_update_client_group(self, client):
        """Test that CSV import can update a client's group."""
        c, _, cm, *_ = client
        cm.create_client_group("Group1")
        cm.create_client_group("Group2")
        
        # Create a client in Group1
        cm.create_client("aa:bb:cc:dd:ee:ff", "Group1", name="TestClient")
        
        # Import CSV to move client to Group2
        csv_content = "MAC Address,Client Name,Client Group\naa:bb:cc:dd:ee:ff,TestClient,Group2\n"
        
        from io import BytesIO
        data = {
            'file': (BytesIO(csv_content.encode()), 'test.csv')
        }
        
        resp = c.post("/api/clients/csv-import", data=data, content_type='multipart/form-data')
        assert resp.status_code == 201
        result = resp.get_json()
        assert result["results"]["updated"] == 1
        
        # Verify the client was moved to Group2
        updated_client = cm.get_client("aa:bb:cc:dd:ee:ff")
        assert updated_client.client_group_name == "Group2"
