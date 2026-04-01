"""
Database Persistence Layer

Replaces JSON-based persistence with SQLite for better scalability.
Provides methods to load/save all data types.
"""

import logging
from typing import List
from datetime import datetime

from src.database import Database
from src.models import (
    Device, DeviceGroup, Client, ClientGroup, MABPolicy,
    AuthenticationLog, AuthenticationOutcome, PolicyDecision
)

logger = logging.getLogger(__name__)


class DevicePersistence:
    """Persistence for devices and device groups."""

    @staticmethod
    def load_devices() -> List[Device]:
        """Load all devices from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM devices")
        rows = cursor.fetchall()
        conn.close()
        
        devices = []
        for row in rows:
            devices.append(Device(
                id=row['id'],
                ip_address=row['ip_address'],
                shared_secret=row['shared_secret'],
                device_group_id=row['device_group_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            ))
        return devices

    @staticmethod
    def save_devices(devices: List[Device]) -> None:
        """Save all devices to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing devices
        cursor.execute("DELETE FROM devices")
        
        # Insert new devices
        for device in devices:
            cursor.execute("""
                INSERT INTO devices (id, ip_address, shared_secret, device_group_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (device.id, device.ip_address, device.shared_secret, device.device_group_id,
                  device.created_at.isoformat(), device.updated_at.isoformat()))
        
        conn.commit()
        conn.close()

    @staticmethod
    def load_device_groups() -> List[DeviceGroup]:
        """Load all device groups from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM device_groups")
        rows = cursor.fetchall()
        conn.close()
        
        groups = []
        for row in rows:
            groups.append(DeviceGroup(
                id=row['id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            ))
        return groups

    @staticmethod
    def save_device_groups(groups: List[DeviceGroup]) -> None:
        """Save all device groups to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing groups
        cursor.execute("DELETE FROM device_groups")
        
        # Insert new groups
        for group in groups:
            cursor.execute("""
                INSERT INTO device_groups (id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (group.id, group.name, group.created_at.isoformat(), group.updated_at.isoformat()))
        
        conn.commit()
        conn.close()


class ClientPersistence:
    """Persistence for clients and client groups."""

    @staticmethod
    def load_clients() -> List[Client]:
        """Load all clients from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM clients")
        rows = cursor.fetchall()
        conn.close()
        
        clients = []
        for row in rows:
            clients.append(Client(
                mac_address=row['mac_address'],
                client_group_id=row['client_group_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            ))
        return clients

    @staticmethod
    def save_clients(clients: List[Client]) -> None:
        """Save all clients to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing clients
        cursor.execute("DELETE FROM clients")
        
        # Insert new clients
        for client in clients:
            cursor.execute("""
                INSERT INTO clients (mac_address, client_group_id, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (client.mac_address, client.client_group_id,
                  client.created_at.isoformat(), client.updated_at.isoformat()))
        
        conn.commit()
        conn.close()

    @staticmethod
    def load_client_groups() -> List[ClientGroup]:
        """Load all client groups from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM client_groups")
        rows = cursor.fetchall()
        conn.close()
        
        groups = []
        for row in rows:
            groups.append(ClientGroup(
                id=row['id'],
                name=row['name'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            ))
        return groups

    @staticmethod
    def save_client_groups(groups: List[ClientGroup]) -> None:
        """Save all client groups to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing groups
        cursor.execute("DELETE FROM client_groups")
        
        # Insert new groups
        for group in groups:
            cursor.execute("""
                INSERT INTO client_groups (id, name, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (group.id, group.name, group.created_at.isoformat(), group.updated_at.isoformat()))
        
        conn.commit()
        conn.close()


class PolicyPersistence:
    """Persistence for policies."""

    @staticmethod
    def load_policies() -> List[MABPolicy]:
        """Load all policies from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM policies")
        rows = cursor.fetchall()
        conn.close()
        
        policies = []
        for row in rows:
            policies.append(MABPolicy(
                id=row['id'],
                client_group_id=row['client_group_id'],
                decision=PolicyDecision(row['decision']),
                vlan_id=row['vlan_id'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
            ))
        return policies

    @staticmethod
    def save_policies(policies: List[MABPolicy]) -> None:
        """Save all policies to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing policies
        cursor.execute("DELETE FROM policies")
        
        # Insert new policies
        for policy in policies:
            cursor.execute("""
                INSERT INTO policies (id, client_group_id, decision, vlan_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (policy.id, policy.client_group_id, policy.decision.value, policy.vlan_id,
                  policy.created_at.isoformat(), policy.updated_at.isoformat()))
        
        conn.commit()
        conn.close()


class LogPersistence:
    """Persistence for authentication logs."""

    @staticmethod
    def load_logs() -> List[AuthenticationLog]:
        """Load all logs from database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM auth_logs ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        conn.close()
        
        logs = []
        for row in rows:
            logs.append(AuthenticationLog(
                id=row['id'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                client_mac=row['client_mac'],
                device_id=row['device_id'],
                outcome=AuthenticationOutcome(row['outcome']),
                vlan_id=row['vlan_id'],
                policy_decision=row['policy_decision'],
                created_at=datetime.fromisoformat(row['created_at']),
            ))
        return logs

    @staticmethod
    def save_log(log: AuthenticationLog) -> None:
        """Save a single log entry to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO auth_logs (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_decision, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (log.id, log.timestamp.isoformat(), log.client_mac, log.device_id,
              log.outcome.value, log.vlan_id, log.policy_decision, log.created_at.isoformat()))
        
        conn.commit()
        conn.close()

    @staticmethod
    def save_logs(logs: List[AuthenticationLog]) -> None:
        """Save all logs to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Clear existing logs
        cursor.execute("DELETE FROM auth_logs")
        
        # Insert new logs
        for log in logs:
            cursor.execute("""
                INSERT INTO auth_logs (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_decision, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (log.id, log.timestamp.isoformat(), log.client_mac, log.device_id,
                  log.outcome.value, log.vlan_id, log.policy_decision, log.created_at.isoformat()))
        
        conn.commit()
        conn.close()
