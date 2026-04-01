"""
Log_Manager component for recording and querying authentication logs.

Implements create_log_entry, list_logs, filter_logs, get_log_entry.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from src.models import AuthenticationLog, AuthenticationOutcome
from src.persistence import LogPersistence


class Log_Manager:
    """
    Records Authentication_Log entries and provides querying capabilities.

    - Logs are stored in reverse chronological order (newest first) when listed.
    - filter_logs supports optional date range, MAC address, and outcome filters.
    - All changes are persisted to logs.json.
    """

    def __init__(self) -> None:
        self._logs: List[AuthenticationLog] = []
        self._load_data()

    def _load_data(self) -> None:
        try:
            self._logs = LogPersistence.load()
        except Exception:
            self._logs = []

    def _save_data(self) -> None:
        LogPersistence.save(self._logs)

    def create_log_entry(
        self,
        client_mac: str,
        device_id: str,
        outcome: AuthenticationOutcome,
        vlan_id: Optional[int] = None,
        policy_name: Optional[str] = None,
        policy_decision: Optional[str] = None,
    ) -> AuthenticationLog:
        """
        Create and persist a new authentication log entry.

        Args:
            client_mac: MAC address of the authenticating client
            device_id: ID of the device that sent the RADIUS request
            outcome: SUCCESS or FAILURE
            vlan_id: VLAN assigned (only for successful authentications with VLAN)
            policy_name: Name of the policy that was applied
            policy_decision: The policy decision (accept_with_vlan, accept_without_vlan, reject)

        Returns:
            The created AuthenticationLog entry
        """
        now = datetime.utcnow()
        log = AuthenticationLog(
            id=str(uuid.uuid4()),
            timestamp=now,
            client_mac=client_mac,
            device_id=device_id,
            outcome=outcome,
            vlan_id=vlan_id,
            policy_name=policy_name,
            policy_decision=policy_decision,
            created_at=now,
        )
        self._logs.append(log)
        # Save individual log entry to database
        from src.db_persistence import LogPersistence as DBLogPersistence
        DBLogPersistence.save_log(log)
        return log

    def list_logs(self) -> List[AuthenticationLog]:
        """Return all logs in reverse chronological order (newest first)."""
        return sorted(self._logs, key=lambda l: l.timestamp, reverse=True)

    def filter_logs(
        self,
        date_start: Optional[datetime] = None,
        date_end: Optional[datetime] = None,
        mac_address: Optional[str] = None,
        outcome: Optional[AuthenticationOutcome] = None,
    ) -> List[AuthenticationLog]:
        """
        Filter logs by any combination of criteria.

        All criteria are optional; only specified criteria are applied.
        Returns results in reverse chronological order.
        """
        results = self._logs
        if date_start is not None:
            results = [l for l in results if l.timestamp >= date_start]
        if date_end is not None:
            results = [l for l in results if l.timestamp <= date_end]
        if mac_address is not None:
            results = [l for l in results if l.client_mac == mac_address]
        if outcome is not None:
            results = [l for l in results if l.outcome == outcome]
        return sorted(results, key=lambda l: l.timestamp, reverse=True)

    def get_log_entry(self, log_id: str) -> Optional[AuthenticationLog]:
        """Retrieve a single log entry by ID."""
        for log in self._logs:
            if log.id == log_id:
                return log
        return None
