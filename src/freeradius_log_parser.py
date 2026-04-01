"""
FreeRADIUS Log Parser

Parses FreeRADIUS authentication logs and creates FNAC log entries.
Monitors /var/log/freeradius/radius.log for authentication events.
Deduplicates logs for the same MAC address within a time window to suppress retransmissions.
"""

import os
import re
import logging
from datetime import datetime, timedelta
from typing import Optional, Set, Dict, Tuple

from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome

logger = logging.getLogger(__name__)

# FreeRADIUS log file path
FREERADIUS_LOG_FILE = "/var/log/freeradius/radius.log"

# Deduplication window: suppress duplicate logs for same MAC within this many seconds
DEDUP_WINDOW_SECONDS = 5

# Regex patterns for parsing FreeRADIUS logs
# Example: Wed Apr  1 18:48:36 2026 : Auth: (1) Login incorrect (pap: Cleartext password does not match "known good" password): [aa:aa:aa:aa:aa:aa] (from client test port 444)
# Also handles: Wed Apr  1 19:03:26 2026 : Auth: (15) Login incorrect (No Auth-Type found: rejecting the user via Post-Auth-Type = Reject): [ecb1e035b860] (from client eltex port 2 cli ec-b1-e0-35-b8-60)
AUTH_FAILURE_PATTERN = re.compile(
    r'(\w+ \w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+:\s+Auth:\s+\(\d+\)\s+.*\[([a-fA-F0-9:]+)\]\s+\(from client (\S+)'
)

# Example: Wed Apr  1 18:35:09 2026 : Auth: (0) Login OK: [aa:aa:aa:aa:aa:aa] (from client test port 444)
AUTH_SUCCESS_PATTERN = re.compile(
    r'(\w+ \w+\s+\d+\s+\d+:\d+:\d+\s+\d+)\s+:\s+Auth:\s+\(\d+\)\s+Login OK:\s+\[([a-fA-F0-9:]+)\]\s+\(from client (\S+)'
)

# Pattern to extract VLAN from response attributes
VLAN_PATTERN = re.compile(r'Tunnel-Private-Group-ID = "(\d+)"')


class FreeRADIUSLogParser:
    """Parses FreeRADIUS logs and creates FNAC log entries."""

    def __init__(self, log_manager: Log_Manager, log_file: str = FREERADIUS_LOG_FILE, 
                 client_manager=None, policy_engine=None):
        self.log_manager = log_manager
        self.log_file = log_file
        self.client_manager = client_manager
        self.policy_engine = policy_engine
        self.processed_lines: Set[str] = set()
        self.last_position = 0
        # Track recent logs: (mac_address, outcome) -> timestamp
        self.recent_logs: Dict[Tuple[str, str], datetime] = {}

    def parse_logs(self) -> int:
        """
        Parse new entries from FreeRADIUS log file.
        
        Returns:
            Number of new log entries created
        """
        if not os.path.exists(self.log_file):
            logger.warning(f"FreeRADIUS log file not found: {self.log_file}")
            return 0

        try:
            with open(self.log_file, 'r') as f:
                # Seek to last position
                f.seek(self.last_position)
                lines = f.readlines()
                self.last_position = f.tell()

            new_entries = 0
            for line in lines:
                if self._process_line(line):
                    new_entries += 1

            # Clean up old entries from dedup cache
            self._cleanup_dedup_cache()

            return new_entries

        except Exception as e:
            logger.error(f"Error parsing FreeRADIUS logs: {e}")
            return 0

    def _is_duplicate(self, mac_address: str, outcome: str) -> bool:
        """
        Check if this is a duplicate log entry within the dedup window.
        
        Returns:
            True if this is a duplicate, False if it's a new event
        """
        key = (mac_address, outcome)
        now = datetime.utcnow()
        
        if key in self.recent_logs:
            last_time = self.recent_logs[key]
            time_diff = (now - last_time).total_seconds()
            
            if time_diff < DEDUP_WINDOW_SECONDS:
                # This is a duplicate within the window
                return True
        
        # Not a duplicate, update the timestamp
        self.recent_logs[key] = now
        return False

    def _cleanup_dedup_cache(self) -> None:
        """Remove old entries from dedup cache."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=DEDUP_WINDOW_SECONDS * 2)
        
        keys_to_remove = [
            key for key, timestamp in self.recent_logs.items()
            if timestamp < cutoff
        ]
        
        for key in keys_to_remove:
            del self.recent_logs[key]

    def _get_policy_name(self, mac_address: str) -> Optional[str]:
        """
        Get the policy name for a MAC address.
        
        Returns:
            Policy ID (name) if found, None otherwise
        """
        if not self.client_manager or not self.policy_engine:
            return None
        
        try:
            # Get client by MAC address
            client = self.client_manager.get_client(mac_address)
            if not client:
                return None
            
            # Get policy by client group
            policy = self.policy_engine.get_policy_by_client_group(client.client_group_id)
            if not policy:
                return None
            
            return policy.id
        except Exception as e:
            logger.debug(f"Error getting policy name for {mac_address}: {e}")
            return None

    def _process_line(self, line: str) -> bool:
        """
        Process a single log line.
        
        Returns:
            True if a new log entry was created, False otherwise
        """
        line = line.strip()
        if not line or line in self.processed_lines:
            return False

        self.processed_lines.add(line)

        # Try to match success pattern
        success_match = AUTH_SUCCESS_PATTERN.search(line)
        if success_match:
            timestamp_str = success_match.group(1)
            mac_address = success_match.group(2)
            device_name = success_match.group(3)
            
            # Check for duplicates
            if self._is_duplicate(mac_address, "success"):
                logger.debug(f"Suppressed duplicate SUCCESS log for {mac_address}")
                return False
            
            try:
                timestamp = self._parse_timestamp(timestamp_str)
                vlan_id = self._extract_vlan(line)
                policy_decision = "accept_with_vlan" if vlan_id else "accept_without_vlan"
                policy_name = self._get_policy_name(mac_address)
                
                # Create log entry with explicit timestamp via log manager
                # The log manager will handle database persistence
                from src.models import AuthenticationOutcome
                log = self.log_manager.create_log_entry(
                    client_mac=mac_address,
                    device_id=device_name,
                    outcome=AuthenticationOutcome.SUCCESS,
                    vlan_id=vlan_id,
                    policy_decision=policy_decision,
                    policy_name=policy_name,
                )
                # Override the timestamp to use the one from FreeRADIUS log
                log.timestamp = timestamp
                log.created_at = timestamp
                
                # Save the corrected log to database
                from src.db_persistence import LogPersistence as DBLogPersistence
                DBLogPersistence.save_log(log)
                
                logger.debug(f"Created SUCCESS log entry for {mac_address}")
                return True
            except Exception as e:
                logger.warning(f"Error processing success log: {e}")
                return False

        # Try to match failure pattern
        failure_match = AUTH_FAILURE_PATTERN.search(line)
        if failure_match:
            timestamp_str = failure_match.group(1)
            mac_address = failure_match.group(2)
            device_name = failure_match.group(3)
            
            # Check for duplicates
            if self._is_duplicate(mac_address, "failure"):
                logger.debug(f"Suppressed duplicate FAILURE log for {mac_address}")
                return False
            
            try:
                timestamp = self._parse_timestamp(timestamp_str)
                policy_name = self._get_policy_name(mac_address)
                
                # Create log entry with explicit timestamp via log manager
                from src.models import AuthenticationOutcome
                log = self.log_manager.create_log_entry(
                    client_mac=mac_address,
                    device_id=device_name,
                    outcome=AuthenticationOutcome.FAILURE,
                    policy_decision="reject",
                    policy_name=policy_name,
                )
                # Override the timestamp to use the one from FreeRADIUS log
                log.timestamp = timestamp
                log.created_at = timestamp
                
                # Save the corrected log to database
                from src.db_persistence import LogPersistence as DBLogPersistence
                DBLogPersistence.save_log(log)
                
                logger.debug(f"Created FAILURE log entry for {mac_address}")
                return True
            except Exception as e:
                logger.warning(f"Error processing failure log: {e}")
                return False

        return False

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse FreeRADIUS timestamp format: 'Wed Apr  1 18:48:36 2026' and convert to GMT+3."""
        try:
            # Parse the timestamp as UTC first
            dt = datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
            # Add 3 hours for GMT+3
            from datetime import timedelta
            dt = dt + timedelta(hours=3)
            return dt
        except ValueError:
            # Fallback to current time if parsing fails
            from datetime import timedelta
            return datetime.utcnow() + timedelta(hours=3)

    def _extract_vlan(self, line: str) -> Optional[int]:
        """Extract VLAN ID from log line if present."""
        match = VLAN_PATTERN.search(line)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
