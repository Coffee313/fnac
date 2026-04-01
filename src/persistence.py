"""
Persistence layer for RADIUS server data.

Handles loading and saving of devices, clients, policies, and logs.
Uses SQLite database for better scalability and performance.
"""

import logging
from typing import List

from src.db_persistence import (
    DevicePersistence as DBDevicePersistence,
    ClientPersistence as DBClientPersistence,
    PolicyPersistence as DBPolicyPersistence,
    LogPersistence as DBLogPersistence,
)
from src.models import Device, DeviceGroup, Client, ClientGroup, MABPolicy, AuthenticationLog

logger = logging.getLogger(__name__)


class DevicePersistence:
    """Persistence for devices and device groups."""

    @staticmethod
    def load() -> tuple:
        """Load devices and device groups from database."""
        try:
            devices = DBDevicePersistence.load_devices()
            groups = DBDevicePersistence.load_device_groups()
            return devices, groups
        except Exception as e:
            logger.error(f"Error loading devices: {e}")
            return [], []

    @staticmethod
    def save(devices: List[Device], groups: List[DeviceGroup]) -> None:
        """Save devices and device groups to database."""
        try:
            DBDevicePersistence.save_device_groups(groups)
            DBDevicePersistence.save_devices(devices)
        except Exception as e:
            logger.error(f"Error saving devices: {e}")


class ClientPersistence:
    """Persistence for clients and client groups."""

    @staticmethod
    def load() -> tuple:
        """Load clients and client groups from database."""
        try:
            clients = DBClientPersistence.load_clients()
            groups = DBClientPersistence.load_client_groups()
            return clients, groups
        except Exception as e:
            logger.error(f"Error loading clients: {e}")
            return [], []

    @staticmethod
    def save(clients: List[Client], groups: List[ClientGroup]) -> None:
        """Save clients and client groups to database."""
        try:
            DBClientPersistence.save_client_groups(groups)
            DBClientPersistence.save_clients(clients)
        except Exception as e:
            logger.error(f"Error saving clients: {e}")


class PolicyPersistence:
    """Persistence for policies."""

    @staticmethod
    def load() -> List[MABPolicy]:
        """Load policies from database."""
        try:
            return DBPolicyPersistence.load_policies()
        except Exception as e:
            logger.error(f"Error loading policies: {e}")
            return []

    @staticmethod
    def save(policies: List[MABPolicy]) -> None:
        """Save policies to database."""
        try:
            DBPolicyPersistence.save_policies(policies)
        except Exception as e:
            logger.error(f"Error saving policies: {e}")


class LogPersistence:
    """Persistence for authentication logs."""

    @staticmethod
    def load() -> List[AuthenticationLog]:
        """Load logs from database."""
        try:
            return DBLogPersistence.load_logs()
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
            return []

    @staticmethod
    def save(logs: List[AuthenticationLog]) -> None:
        """Save logs to database."""
        try:
            DBLogPersistence.save_logs(logs)
        except Exception as e:
            logger.error(f"Error saving logs: {e}")
