"""
Policy_Engine component for managing MAB policies and evaluating authentication decisions.

Implements create/update/delete/get/list for MAB_Policy and evaluate_policy().
"""

from typing import Dict, List, Optional, Tuple
from src.models import MABPolicy, PolicyDecision
from src.persistence import PolicyPersistence


class PolicyEngineError(Exception):
    """Base exception for Policy_Engine errors."""
    pass


class PolicyNotFoundError(PolicyEngineError):
    """Raised when a policy is not found."""
    pass


class DuplicatePolicyError(PolicyEngineError):
    """Raised when a policy already exists for a client group."""
    pass


class InvalidVLANError(PolicyEngineError):
    """Raised when a VLAN ID is out of the valid range (1-4094)."""
    pass


class Policy_Engine:
    """
    Manages MAB_Policy entities and evaluates authentication decisions.

    Enforces:
    - One policy per client group
    - VLAN ID in range 1-4094 when decision is ACCEPT_WITH_VLAN
    - Default REJECT for missing policies
    - Persistence of all changes to policies.json
    """

    def __init__(self) -> None:
        self._policies: Dict[str, MABPolicy] = {}          # keyed by policy id
        self._group_index: Dict[str, str] = {}             # client_group_id -> policy id
        self._load_data()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_data(self) -> None:
        try:
            policies = PolicyPersistence.load()
            self._policies = {p.id: p for p in policies}
            self._group_index = {p.client_group_id: p.id for p in policies}
        except Exception:
            self._policies = {}
            self._group_index = {}

    def _save_data(self) -> None:
        PolicyPersistence.save(list(self._policies.values()))

    @staticmethod
    def _validate_vlan(decision: PolicyDecision, vlan_id: Optional[int]) -> None:
        if decision == PolicyDecision.ACCEPT_WITH_VLAN:
            if vlan_id is None or not (1 <= vlan_id <= 4094):
                raise InvalidVLANError(
                    f"VLAN ID must be between 1 and 4094 for ACCEPT_WITH_VLAN decision"
                )

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def create_policy(
        self,
        policy_id: str,
        client_group_id: str,
        decision: PolicyDecision,
        vlan_id: Optional[int] = None,
    ) -> MABPolicy:
        """
        Create a new MAB policy.

        Raises:
            DuplicatePolicyError: If a policy already exists for client_group_id
            InvalidVLANError: If decision is ACCEPT_WITH_VLAN and vlan_id is invalid
        """
        if client_group_id in self._group_index:
            raise DuplicatePolicyError(
                f"A policy already exists for client group '{client_group_id}'"
            )
        self._validate_vlan(decision, vlan_id)

        policy = MABPolicy(
            id=policy_id,
            client_group_id=client_group_id,
            decision=decision,
            vlan_id=vlan_id if decision == PolicyDecision.ACCEPT_WITH_VLAN else None,
        )
        self._policies[policy_id] = policy
        self._group_index[client_group_id] = policy_id
        self._save_data()
        return policy

    def update_policy(
        self,
        policy_id: str,
        decision: Optional[PolicyDecision] = None,
        vlan_id: Optional[int] = None,
    ) -> MABPolicy:
        """
        Update an existing policy's decision and/or VLAN ID.

        Raises:
            PolicyNotFoundError: If policy_id does not exist
            InvalidVLANError: If resulting decision is ACCEPT_WITH_VLAN and vlan_id invalid
        """
        if policy_id not in self._policies:
            raise PolicyNotFoundError(f"Policy '{policy_id}' not found")

        policy = self._policies[policy_id]
        new_decision = decision if decision is not None else policy.decision
        new_vlan = vlan_id if vlan_id is not None else policy.vlan_id

        self._validate_vlan(new_decision, new_vlan)

        policy.decision = new_decision
        policy.vlan_id = new_vlan if new_decision == PolicyDecision.ACCEPT_WITH_VLAN else None

        from datetime import datetime
        policy.updated_at = datetime.utcnow()

        self._save_data()
        return policy

    def delete_policy(self, policy_id: str) -> None:
        """
        Delete a policy.

        Raises:
            PolicyNotFoundError: If policy_id does not exist
        """
        if policy_id not in self._policies:
            raise PolicyNotFoundError(f"Policy '{policy_id}' not found")

        policy = self._policies.pop(policy_id)
        self._group_index.pop(policy.client_group_id, None)
        self._save_data()

    def get_policy(self, policy_id: str) -> Optional[MABPolicy]:
        return self._policies.get(policy_id)

    def get_policy_by_client_group(self, client_group_id: str) -> Optional[MABPolicy]:
        pid = self._group_index.get(client_group_id)
        return self._policies.get(pid) if pid else None

    def list_policies(self) -> List[MABPolicy]:
        return list(self._policies.values())

    def evaluate_policy(
        self, client_group_id: str
    ) -> Tuple[PolicyDecision, Optional[int]]:
        """
        Evaluate the policy for a client group.

        Returns (decision, vlan_id). Defaults to (REJECT, None) if no policy exists.
        """
        policy = self.get_policy_by_client_group(client_group_id)
        if policy is None:
            return PolicyDecision.REJECT, None
        return policy.decision, policy.vlan_id
