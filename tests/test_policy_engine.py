"""
Tests for Policy_Engine component.

Covers Properties 16-22 (Requirements 3.1-3.7).
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import src.persistence as _persistence_mod
from src.models import MABPolicy, PolicyDecision
from src.policy_engine import (
    DuplicatePolicyError,
    InvalidVLANError,
    Policy_Engine,
    PolicyNotFoundError,
)

from hypothesis import given, settings, assume
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
def engine(mock_config):
    return Policy_Engine()


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

class TestPolicyCreation:
    def test_create_policy_accept_with_vlan(self, engine):
        p = engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=100)
        assert p.id == "p1"
        assert p.client_group_id == "g1"
        assert p.decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert p.vlan_id == 100

    def test_create_policy_accept_without_vlan(self, engine):
        p = engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
        assert p.decision == PolicyDecision.ACCEPT_WITHOUT_VLAN
        assert p.vlan_id is None

    def test_create_policy_reject(self, engine):
        p = engine.create_policy("p1", "g1", PolicyDecision.REJECT)
        assert p.decision == PolicyDecision.REJECT

    def test_create_duplicate_group_raises_error(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.REJECT)
        with pytest.raises(DuplicatePolicyError):
            engine.create_policy("p2", "g1", PolicyDecision.ACCEPT_WITHOUT_VLAN)

    def test_create_accept_with_vlan_invalid_vlan_raises_error(self, engine):
        with pytest.raises(InvalidVLANError):
            engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=0)
        with pytest.raises(InvalidVLANError):
            engine.create_policy("p2", "g2", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=4095)
        with pytest.raises(InvalidVLANError):
            engine.create_policy("p3", "g3", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=None)


class TestPolicyUpdate:
    def test_update_decision(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.REJECT)
        updated = engine.update_policy("p1", decision=PolicyDecision.ACCEPT_WITHOUT_VLAN)
        assert updated.decision == PolicyDecision.ACCEPT_WITHOUT_VLAN

    def test_update_vlan(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=100)
        updated = engine.update_policy("p1", vlan_id=200)
        assert updated.vlan_id == 200

    def test_update_nonexistent_raises_error(self, engine):
        with pytest.raises(PolicyNotFoundError):
            engine.update_policy("nonexistent", decision=PolicyDecision.REJECT)


class TestPolicyDeletion:
    def test_delete_policy(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.REJECT)
        engine.delete_policy("p1")
        assert engine.get_policy("p1") is None

    def test_delete_nonexistent_raises_error(self, engine):
        with pytest.raises(PolicyNotFoundError):
            engine.delete_policy("nonexistent")


class TestPolicyEvaluation:
    def test_evaluate_accept_with_vlan(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=100)
        decision, vlan = engine.evaluate_policy("g1")
        assert decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert vlan == 100

    def test_evaluate_accept_without_vlan(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITHOUT_VLAN)
        decision, vlan = engine.evaluate_policy("g1")
        assert decision == PolicyDecision.ACCEPT_WITHOUT_VLAN
        assert vlan is None

    def test_evaluate_reject(self, engine):
        engine.create_policy("p1", "g1", PolicyDecision.REJECT)
        decision, vlan = engine.evaluate_policy("g1")
        assert decision == PolicyDecision.REJECT

    def test_evaluate_missing_policy_returns_reject(self, engine):
        decision, vlan = engine.evaluate_policy("nonexistent-group")
        assert decision == PolicyDecision.REJECT
        assert vlan is None

    def test_persistence_across_instances(self, engine, mock_config):
        engine.create_policy("p1", "g1", PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=42)
        new_engine = Policy_Engine()
        decision, vlan = new_engine.evaluate_policy("g1")
        assert decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert vlan == 42


# ---------------------------------------------------------------------------
# Property-Based Tests
# ---------------------------------------------------------------------------

_text_id = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters="\x00"),
    min_size=1,
    max_size=30,
)
_vlan_id = st.integers(min_value=1, max_value=4094)
_decision = st.sampled_from(list(PolicyDecision))


def _fresh_engine():
    import contextlib

    @contextlib.contextmanager
    def _ctx():
        with tempfile.TemporaryDirectory() as d:
            with patch.object(_persistence_mod, "DEVICES_FILE", os.path.join(d, "devices.json")), \
                 patch.object(_persistence_mod, "CLIENTS_FILE", os.path.join(d, "clients.json")), \
                 patch.object(_persistence_mod, "POLICIES_FILE", os.path.join(d, "policies.json")), \
                 patch.object(_persistence_mod, "LOGS_FILE", os.path.join(d, "logs.json")):
                yield Policy_Engine()

    return _ctx()


class TestPropertyPolicyEngine:
    """Properties 16-22: Policy_Engine correctness. Validates: Requirements 3.1-3.7"""

    @settings(max_examples=50)
    @given(pid=_text_id, gid=_text_id, vlan=_vlan_id)
    def test_property16_policy_creation_maps_group_to_decision(self, pid, gid, vlan):
        """Feature: simple-radius-server, Property 16: Policy Creation Maps Client Group to Decision"""
        with _fresh_engine() as eng:
            p = eng.create_policy(pid, gid, PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=vlan)
        assert p.client_group_id == gid
        assert p.decision == PolicyDecision.ACCEPT_WITH_VLAN

    @settings(max_examples=50)
    @given(pid=_text_id, gid=_text_id, vlan=_vlan_id)
    def test_property17_accept_with_vlan_stores_vlan(self, pid, gid, vlan):
        """Feature: simple-radius-server, Property 17: Policy Accept with VLAN Configuration"""
        with _fresh_engine() as eng:
            eng.create_policy(pid, gid, PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=vlan)
            decision, returned_vlan = eng.evaluate_policy(gid)
        assert decision == PolicyDecision.ACCEPT_WITH_VLAN
        assert returned_vlan == vlan

    @settings(max_examples=50)
    @given(pid=_text_id, gid=_text_id)
    def test_property18_accept_without_vlan_no_vlan(self, pid, gid):
        """Feature: simple-radius-server, Property 18: Policy Accept without VLAN Configuration"""
        with _fresh_engine() as eng:
            eng.create_policy(pid, gid, PolicyDecision.ACCEPT_WITHOUT_VLAN)
            decision, vlan = eng.evaluate_policy(gid)
        assert decision == PolicyDecision.ACCEPT_WITHOUT_VLAN
        assert vlan is None

    @settings(max_examples=50)
    @given(pid=_text_id, gid=_text_id)
    def test_property19_reject_configuration(self, pid, gid):
        """Feature: simple-radius-server, Property 19: Policy Reject Configuration"""
        with _fresh_engine() as eng:
            eng.create_policy(pid, gid, PolicyDecision.REJECT)
            decision, vlan = eng.evaluate_policy(gid)
        assert decision == PolicyDecision.REJECT

    @settings(max_examples=30)
    @given(pid=_text_id, gid=_text_id, vlan1=_vlan_id, vlan2=_vlan_id)
    def test_property20_policy_update_applies_changes(self, pid, gid, vlan1, vlan2):
        """Feature: simple-radius-server, Property 20: Policy Update Applies Changes"""
        with _fresh_engine() as eng:
            eng.create_policy(pid, gid, PolicyDecision.ACCEPT_WITH_VLAN, vlan_id=vlan1)
            eng.update_policy(pid, vlan_id=vlan2)
            _, returned_vlan = eng.evaluate_policy(gid)
        assert returned_vlan == vlan2

    @settings(max_examples=30)
    @given(pid=_text_id, gid=_text_id)
    def test_property21_policy_removal_is_complete(self, pid, gid):
        """Feature: simple-radius-server, Property 21: Policy Removal is Complete"""
        with _fresh_engine() as eng:
            eng.create_policy(pid, gid, PolicyDecision.REJECT)
            eng.delete_policy(pid)
            found = eng.get_policy(pid)
            listed = [p.id for p in eng.list_policies()]
        assert found is None
        assert pid not in listed

    @settings(max_examples=30)
    @given(
        policies=st.lists(
            st.tuples(_text_id, _text_id),
            min_size=1,
            max_size=5,
            unique_by=lambda t: t[0],  # unique policy ids
        )
    )
    def test_property22_policy_listing_is_complete_and_accurate(self, policies):
        """Feature: simple-radius-server, Property 22: Policy Listing is Complete and Accurate"""
        # Also ensure unique group ids
        assume(len({gid for _, gid in policies}) == len(policies))

        with _fresh_engine() as eng:
            created_ids = set()
            for pid, gid in policies:
                eng.create_policy(pid, gid, PolicyDecision.REJECT)
                created_ids.add(pid)
            listed_ids = {p.id for p in eng.list_policies()}

        assert listed_ids == created_ids
