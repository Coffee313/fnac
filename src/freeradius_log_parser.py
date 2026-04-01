"""
FreeRADIUS Log Parser

Parses FreeRADIUS authentication logs and creates FNAC log entries.
Monitors /var/log/freeradius/radius.log for authentication events.
"""

import os
import re
import logging
from datetime import datetime
from typing import Optional, Set, Tuple

from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome

logger = logging.getLogger(__name__)

# FreeRADIUS log file path
FREERADIUS_LOG_FILE = "/var/log/freeradius/radius.log"

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

    def __init__(self, log_manager: Log_Manager, log_file: str = FREERADIUS_LOG_FILE):
        self.log_manager = log_manager
        self.log_file = log_file
        self.processed_lines: Set[str] = set()
        self.last_position = 0

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

            return new_entries

        except Exception as e:
            logger.error(f"Error parsing FreeRADIUS logs: {e}")
            return 0

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
            
            try:
                timestamp = self._parse_timestamp(timestamp_str)
                vlan_id = self._extract_vlan(line)
                policy_decision = "accept_with_vlan" if vlan_id else "accept_without_vlan"
                
                self.log_manager.create_log_entry(
                    client_mac=mac_address,
                    device_id=device_name,
                    outcome=AuthenticationOutcome.SUCCESS,
                    vlan_id=vlan_id,
                    policy_decision=policy_decision,
                )
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
            
            try:
                timestamp = self._parse_timestamp(timestamp_str)
                
                self.log_manager.create_log_entry(
                    client_mac=mac_address,
                    device_id=device_name,
                    outcome=AuthenticationOutcome.FAILURE,
                    policy_decision="reject",
                )
                logger.debug(f"Created FAILURE log entry for {mac_address}")
                return True
            except Exception as e:
                logger.warning(f"Error processing failure log: {e}")
                return False

        return False

    def _parse_timestamp(self, timestamp_str: str) -> datetime:
        """Parse FreeRADIUS timestamp format: 'Wed Apr  1 18:48:36 2026'"""
        try:
            return datetime.strptime(timestamp_str, "%a %b %d %H:%M:%S %Y")
        except ValueError:
            # Fallback to current time if parsing fails
            return datetime.utcnow()

    def _extract_vlan(self, line: str) -> Optional[int]:
        """Extract VLAN ID from log line if present."""
        match = VLAN_PATTERN.search(line)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
