"""
JSON-based persistence layer for RADIUS server data.

Implements atomic file write operations and data validation on load.
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.config import CLIENTS_FILE, DEVICES_FILE, LOGS_FILE, POLICIES_FILE
from src.models import (
    AuthenticationLog,
    AuthenticationOutcome,
    Client,
    ClientGroup,
    Device,
    DeviceGroup,
    MABPolicy,
    PolicyDecision,
)


class PersistenceError(Exception):
    """Base exception for persistence layer errors."""
    pass


class DataValidationError(PersistenceError):
    """Raised when loaded data fails validation."""
    pass


class AtomicFileWriter:
    """Handles atomic file write operations using temp file and rename."""

    @staticmethod
    def write_atomic(file_path: str, data: Any) -> None:
        """
        Write data to file atomically.

        Writes to a temporary file first, then renames it to the target path.
        This prevents corruption if the process is interrupted during write.

        Args:
            file_path: Path to the target file
            data: Data to write (will be JSON serialized)

        Raises:
            PersistenceError: If write operation fails
        """
        try:
            # Ensure directory exists
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

            # Write to temporary file in the same directory
            # This ensures temp file is on the same filesystem for atomic rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=str(Path(file_path).parent),
                prefix=".tmp_",
                suffix=".json"
            )

            try:
                with os.fdopen(temp_fd, 'w') as temp_file:
                    json.dump(data, temp_file, indent=2, default=_json_serializer)
                    temp_file.flush()
                    os.fsync(temp_file.fileno())

                # Atomic rename
                os.replace(temp_path, file_path)
            except Exception:
                # Clean up temp file if something goes wrong
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
                raise

        except Exception as e:
            raise PersistenceError(f"Failed to write to {file_path}: {str(e)}")


def _json_serializer(obj: Any) -> Any:
    """JSON serializer for objects not serializable by default json code."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (PolicyDecision, AuthenticationOutcome)):
        return obj.value
    raise TypeError(f"Type {type(obj)} not serializable")


def _parse_datetime(date_string: str) -> datetime:
    """Parse ISO format datetime string."""
    try:
        return datetime.fromisoformat(date_string)
    except (ValueError, TypeError):
        raise DataValidationError(f"Invalid datetime format: {date_string}")


class DevicePersistence:
    """Handles persistence of Device and DeviceGroup data."""

    @staticmethod
    def save(devices: List[Device], device_groups: List[DeviceGroup]) -> None:
        """
        Save devices and device groups to persistent storage.

        Args:
            devices: List of Device objects
            device_groups: List of DeviceGroup objects

        Raises:
            PersistenceError: If save operation fails
        """
        data = {
            "devices": [
                {
                    "id": d.id,
                    "ip_address": d.ip_address,
                    "shared_secret": d.shared_secret,
                    "device_group_id": d.device_group_id,
                    "created_at": d.created_at,
                    "updated_at": d.updated_at,
                }
                for d in devices
            ],
            "device_groups": [
                {
                    "id": dg.id,
                    "name": dg.name,
                    "created_at": dg.created_at,
                    "updated_at": dg.updated_at,
                }
                for dg in device_groups
            ],
        }
        AtomicFileWriter.write_atomic(DEVICES_FILE, data)

    @staticmethod
    def load() -> Tuple[List[Device], List[DeviceGroup]]:
        """
        Load devices and device groups from persistent storage.

        Validates data integrity on load.

        Returns:
            Tuple of (devices list, device_groups list)

        Raises:
            DataValidationError: If loaded data is corrupted or invalid
            PersistenceError: If load operation fails
        """
        if not os.path.exists(DEVICES_FILE):
            return [], []

        try:
            with open(DEVICES_FILE, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Corrupted devices.json: {str(e)}")
        except Exception as e:
            raise PersistenceError(f"Failed to read devices.json: {str(e)}")

        devices = []
        device_groups = []

        # Validate and load device groups
        try:
            for dg_data in data.get("device_groups", []):
                DevicePersistence._validate_device_group_data(dg_data)
                device_groups.append(
                    DeviceGroup(
                        id=dg_data["id"],
                        name=dg_data["name"],
                        created_at=_parse_datetime(dg_data["created_at"]),
                        updated_at=_parse_datetime(dg_data["updated_at"]),
                    )
                )
        except (KeyError, TypeError) as e:
            raise DataValidationError(f"Invalid device group data: {str(e)}")

        # Validate and load devices
        try:
            for d_data in data.get("devices", []):
                DevicePersistence._validate_device_data(d_data)
                devices.append(
                    Device(
                        id=d_data["id"],
                        ip_address=d_data["ip_address"],
                        shared_secret=d_data["shared_secret"],
                        device_group_id=d_data["device_group_id"],
                        created_at=_parse_datetime(d_data["created_at"]),
                        updated_at=_parse_datetime(d_data["updated_at"]),
                    )
                )
        except (KeyError, TypeError) as e:
            raise DataValidationError(f"Invalid device data: {str(e)}")

        return devices, device_groups

    @staticmethod
    def _validate_device_data(data: Dict[str, Any]) -> None:
        """Validate device data structure."""
        required_fields = {"id", "ip_address", "shared_secret", "device_group_id", "created_at", "updated_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError(f"Missing required fields in device data")
        if not isinstance(data["id"], str) or not data["id"]:
            raise DataValidationError("Device id must be non-empty string")
        if not isinstance(data["ip_address"], str) or not data["ip_address"]:
            raise DataValidationError("Device ip_address must be non-empty string")
        if not isinstance(data["shared_secret"], str) or not data["shared_secret"]:
            raise DataValidationError("Device shared_secret must be non-empty string")
        if not isinstance(data["device_group_id"], str) or not data["device_group_id"]:
            raise DataValidationError("Device device_group_id must be non-empty string")

    @staticmethod
    def _validate_device_group_data(data: Dict[str, Any]) -> None:
        """Validate device group data structure."""
        required_fields = {"id", "name", "created_at", "updated_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError("Missing required fields in device group data")
        if not isinstance(data["id"], str) or not data["id"]:
            raise DataValidationError("Device group id must be non-empty string")
        if not isinstance(data["name"], str) or not data["name"]:
            raise DataValidationError("Device group name must be non-empty string")


class ClientPersistence:
    """Handles persistence of Client and ClientGroup data."""

    @staticmethod
    def save(clients: List[Client], client_groups: List[ClientGroup]) -> None:
        """
        Save clients and client groups to persistent storage.

        Args:
            clients: List of Client objects
            client_groups: List of ClientGroup objects

        Raises:
            PersistenceError: If save operation fails
        """
        data = {
            "clients": [
                {
                    "mac_address": c.mac_address,
                    "client_group_id": c.client_group_id,
                    "created_at": c.created_at,
                    "updated_at": c.updated_at,
                }
                for c in clients
            ],
            "client_groups": [
                {
                    "id": cg.id,
                    "name": cg.name,
                    "created_at": cg.created_at,
                    "updated_at": cg.updated_at,
                }
                for cg in client_groups
            ],
        }
        AtomicFileWriter.write_atomic(CLIENTS_FILE, data)

    @staticmethod
    def load() -> Tuple[List[Client], List[ClientGroup]]:
        """
        Load clients and client groups from persistent storage.

        Validates data integrity on load.

        Returns:
            Tuple of (clients list, client_groups list)

        Raises:
            DataValidationError: If loaded data is corrupted or invalid
            PersistenceError: If load operation fails
        """
        if not os.path.exists(CLIENTS_FILE):
            return [], []

        try:
            with open(CLIENTS_FILE, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Corrupted clients.json: {str(e)}")
        except Exception as e:
            raise PersistenceError(f"Failed to read clients.json: {str(e)}")

        clients = []
        client_groups = []

        # Validate and load client groups
        try:
            for cg_data in data.get("client_groups", []):
                ClientPersistence._validate_client_group_data(cg_data)
                client_groups.append(
                    ClientGroup(
                        id=cg_data["id"],
                        name=cg_data["name"],
                        created_at=_parse_datetime(cg_data["created_at"]),
                        updated_at=_parse_datetime(cg_data["updated_at"]),
                    )
                )
        except (KeyError, TypeError) as e:
            raise DataValidationError(f"Invalid client group data: {str(e)}")

        # Validate and load clients
        try:
            for c_data in data.get("clients", []):
                ClientPersistence._validate_client_data(c_data)
                clients.append(
                    Client(
                        mac_address=c_data["mac_address"],
                        client_group_id=c_data["client_group_id"],
                        created_at=_parse_datetime(c_data["created_at"]),
                        updated_at=_parse_datetime(c_data["updated_at"]),
                    )
                )
        except (KeyError, TypeError) as e:
            raise DataValidationError(f"Invalid client data: {str(e)}")

        return clients, client_groups

    @staticmethod
    def _validate_client_data(data: Dict[str, Any]) -> None:
        """Validate client data structure."""
        required_fields = {"mac_address", "client_group_id", "created_at", "updated_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError("Missing required fields in client data")
        if not isinstance(data["mac_address"], str) or not data["mac_address"]:
            raise DataValidationError("Client mac_address must be non-empty string")
        if not isinstance(data["client_group_id"], str) or not data["client_group_id"]:
            raise DataValidationError("Client client_group_id must be non-empty string")

    @staticmethod
    def _validate_client_group_data(data: Dict[str, Any]) -> None:
        """Validate client group data structure."""
        required_fields = {"id", "name", "created_at", "updated_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError("Missing required fields in client group data")
        if not isinstance(data["id"], str) or not data["id"]:
            raise DataValidationError("Client group id must be non-empty string")
        if not isinstance(data["name"], str) or not data["name"]:
            raise DataValidationError("Client group name must be non-empty string")


class PolicyPersistence:
    """Handles persistence of MABPolicy data."""

    @staticmethod
    def save(policies: List[MABPolicy]) -> None:
        """
        Save policies to persistent storage.

        Args:
            policies: List of MABPolicy objects

        Raises:
            PersistenceError: If save operation fails
        """
        data = {
            "policies": [
                {
                    "id": p.id,
                    "client_group_id": p.client_group_id,
                    "decision": p.decision.value,
                    "vlan_id": p.vlan_id,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                }
                for p in policies
            ],
        }
        AtomicFileWriter.write_atomic(POLICIES_FILE, data)

    @staticmethod
    def load() -> List[MABPolicy]:
        """
        Load policies from persistent storage.

        Validates data integrity on load.

        Returns:
            List of MABPolicy objects

        Raises:
            DataValidationError: If loaded data is corrupted or invalid
            PersistenceError: If load operation fails
        """
        if not os.path.exists(POLICIES_FILE):
            return []

        try:
            with open(POLICIES_FILE, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Corrupted policies.json: {str(e)}")
        except Exception as e:
            raise PersistenceError(f"Failed to read policies.json: {str(e)}")

        policies = []

        try:
            for p_data in data.get("policies", []):
                PolicyPersistence._validate_policy_data(p_data)
                decision = PolicyDecision(p_data["decision"])
                policies.append(
                    MABPolicy(
                        id=p_data["id"],
                        client_group_id=p_data["client_group_id"],
                        decision=decision,
                        vlan_id=p_data.get("vlan_id"),
                        created_at=_parse_datetime(p_data["created_at"]),
                        updated_at=_parse_datetime(p_data["updated_at"]),
                    )
                )
        except (KeyError, TypeError, ValueError) as e:
            raise DataValidationError(f"Invalid policy data: {str(e)}")

        return policies

    @staticmethod
    def _validate_policy_data(data: Dict[str, Any]) -> None:
        """Validate policy data structure."""
        required_fields = {"id", "client_group_id", "decision", "created_at", "updated_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError("Missing required fields in policy data")
        if not isinstance(data["id"], str) or not data["id"]:
            raise DataValidationError("Policy id must be non-empty string")
        if not isinstance(data["client_group_id"], str) or not data["client_group_id"]:
            raise DataValidationError("Policy client_group_id must be non-empty string")
        if data["decision"] not in [d.value for d in PolicyDecision]:
            raise DataValidationError(f"Invalid policy decision: {data['decision']}")
        if data.get("vlan_id") is not None and not isinstance(data["vlan_id"], int):
            raise DataValidationError("Policy vlan_id must be integer or null")


class LogPersistence:
    """Handles persistence of AuthenticationLog data."""

    @staticmethod
    def save(logs: List[AuthenticationLog]) -> None:
        """
        Save authentication logs to persistent storage.

        Args:
            logs: List of AuthenticationLog objects

        Raises:
            PersistenceError: If save operation fails
        """
        data = {
            "logs": [
                {
                    "id": log.id,
                    "timestamp": log.timestamp,
                    "client_mac": log.client_mac,
                    "device_id": log.device_id,
                    "outcome": log.outcome.value,
                    "vlan_id": log.vlan_id,
                    "created_at": log.created_at,
                }
                for log in logs
            ],
        }
        AtomicFileWriter.write_atomic(LOGS_FILE, data)

    @staticmethod
    def load() -> List[AuthenticationLog]:
        """
        Load authentication logs from persistent storage.

        Validates data integrity on load.

        Returns:
            List of AuthenticationLog objects

        Raises:
            DataValidationError: If loaded data is corrupted or invalid
            PersistenceError: If load operation fails
        """
        if not os.path.exists(LOGS_FILE):
            return []

        try:
            with open(LOGS_FILE, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise DataValidationError(f"Corrupted logs.json: {str(e)}")
        except Exception as e:
            raise PersistenceError(f"Failed to read logs.json: {str(e)}")

        logs = []

        try:
            for log_data in data.get("logs", []):
                LogPersistence._validate_log_data(log_data)
                outcome = AuthenticationOutcome(log_data["outcome"])
                logs.append(
                    AuthenticationLog(
                        id=log_data["id"],
                        timestamp=_parse_datetime(log_data["timestamp"]),
                        client_mac=log_data["client_mac"],
                        device_id=log_data["device_id"],
                        outcome=outcome,
                        vlan_id=log_data.get("vlan_id"),
                        created_at=_parse_datetime(log_data["created_at"]),
                    )
                )
        except (KeyError, TypeError, ValueError) as e:
            raise DataValidationError(f"Invalid log data: {str(e)}")

        return logs

    @staticmethod
    def _validate_log_data(data: Dict[str, Any]) -> None:
        """Validate log data structure."""
        required_fields = {"id", "timestamp", "client_mac", "device_id", "outcome", "created_at"}
        if not required_fields.issubset(data.keys()):
            raise DataValidationError("Missing required fields in log data")
        if not isinstance(data["id"], str) or not data["id"]:
            raise DataValidationError("Log id must be non-empty string")
        if not isinstance(data["client_mac"], str) or not data["client_mac"]:
            raise DataValidationError("Log client_mac must be non-empty string")
        if not isinstance(data["device_id"], str) or not data["device_id"]:
            raise DataValidationError("Log device_id must be non-empty string")
        if data["outcome"] not in [o.value for o in AuthenticationOutcome]:
            raise DataValidationError(f"Invalid log outcome: {data['outcome']}")
        if data.get("vlan_id") is not None and not isinstance(data["vlan_id"], int):
            raise DataValidationError("Log vlan_id must be integer or null")
