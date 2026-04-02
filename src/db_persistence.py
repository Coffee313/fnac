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
            try:
                # Convert sqlite3.Row to dict for easier access
                row_dict = dict(row)
                
                # Try to get name, fall back to id for old schema
                name = row_dict.get('name') or row_dict.get('id')
                
                devices.append(Device(
                    name=name,
                    ip_address=row_dict['ip_address'],
                    shared_secret=row_dict['shared_secret'],
                    device_group_name=row_dict['device_group_name'],
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                    updated_at=datetime.fromisoformat(row_dict['updated_at']),
                ))
            except (KeyError, TypeError) as e:
                logger.warning(f"Error loading device row: {e}, skipping row")
                continue
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
            try:
                cursor.execute("""
                    INSERT INTO devices (name, ip_address, shared_secret, device_group_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (device.name, device.ip_address, device.shared_secret, device.device_group_name,
                      device.created_at.isoformat(), device.updated_at.isoformat()))
            except Exception as e:
                logger.warning(f"Error saving device {device.name}: {e}")
                # Try with old column name if new one fails
                try:
                    cursor.execute("""
                        INSERT INTO devices (name, ip_address, shared_secret, device_group_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (device.name, device.ip_address, device.shared_secret, device.device_group_name,
                          device.created_at.isoformat(), device.updated_at.isoformat()))
                except Exception as e2:
                    logger.error(f"Failed to save device {device.name}: {e2}")
        
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
                INSERT INTO device_groups (name, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (group.name, group.created_at.isoformat(), group.updated_at.isoformat()))
        
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
            try:
                # Convert sqlite3.Row to dict for easier access
                row_dict = dict(row)
                
                # Try to get mac_address, fall back to id for old schema
                mac_address = row_dict.get('mac_address') or row_dict.get('id')
                
                clients.append(Client(
                    mac_address=mac_address,
                    client_group_name=row_dict['client_group_name'],
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                    updated_at=datetime.fromisoformat(row_dict['updated_at']),
                ))
            except (KeyError, TypeError) as e:
                logger.warning(f"Error loading client row: {e}, skipping row")
                continue
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
            try:
                cursor.execute("""
                    INSERT INTO clients (mac_address, client_group_name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (client.mac_address, client.client_group_name,
                      client.created_at.isoformat(), client.updated_at.isoformat()))
            except Exception as e:
                logger.warning(f"Error saving client {client.mac_address}: {e}")
                # Try with old column name if new one fails
                try:
                    cursor.execute("""
                        INSERT INTO clients (mac_address, client_group_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?)
                    """, (client.mac_address, client.client_group_name,
                          client.created_at.isoformat(), client.updated_at.isoformat()))
                except Exception as e2:
                    logger.error(f"Failed to save client {client.mac_address}: {e2}")
        
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
                INSERT INTO client_groups (name, created_at, updated_at)
                VALUES (?, ?, ?)
            """, (group.name, group.created_at.isoformat(), group.updated_at.isoformat()))
        
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
            try:
                # Convert sqlite3.Row to dict for easier access
                row_dict = dict(row)
                
                # Try to get client_group_name, fall back to client_group_id for old schema
                client_group_name = row_dict.get('client_group_name') or row_dict.get('client_group_id')
                
                policies.append(MABPolicy(
                    name=row_dict['name'],
                    client_group_name=client_group_name,
                    decision=PolicyDecision(row_dict['decision']),
                    vlan_id=row_dict['vlan_id'],
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                    updated_at=datetime.fromisoformat(row_dict['updated_at']),
                ))
            except (KeyError, TypeError) as e:
                logger.warning(f"Error loading policy row: {e}, skipping row")
                continue
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
            try:
                cursor.execute("""
                    INSERT INTO policies (name, client_group_name, decision, vlan_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (policy.name, policy.client_group_name, policy.decision.value, policy.vlan_id,
                      policy.created_at.isoformat(), policy.updated_at.isoformat()))
            except Exception as e:
                logger.warning(f"Error saving policy {policy.name}: {e}")
                # Try with old column name if new one fails
                try:
                    cursor.execute("""
                        INSERT INTO policies (name, client_group_id, decision, vlan_id, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (policy.name, policy.client_group_name, policy.decision.value, policy.vlan_id,
                          policy.created_at.isoformat(), policy.updated_at.isoformat()))
                except Exception as e2:
                    logger.error(f"Failed to save policy {policy.name}: {e2}")
        
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
            try:
                # Convert sqlite3.Row to dict for easier access
                row_dict = dict(row)
                
                # Try to get policy_name, it may not exist in old schema
                policy_name = row_dict.get('policy_name') if 'policy_name' in row_dict else None
                
                logs.append(AuthenticationLog(
                    id=row_dict['id'],
                    timestamp=datetime.fromisoformat(row_dict['timestamp']),
                    client_mac=row_dict['client_mac'],
                    device_id=row_dict['device_id'],
                    outcome=AuthenticationOutcome(row_dict['outcome']),
                    vlan_id=row_dict['vlan_id'],
                    policy_decision=row_dict['policy_decision'],
                    policy_name=policy_name,
                    created_at=datetime.fromisoformat(row_dict['created_at']),
                ))
            except (KeyError, TypeError) as e:
                logger.warning(f"Error loading log row: {e}, skipping row")
                continue
        return logs

    @staticmethod
    def save_log(log: AuthenticationLog) -> None:
        """Save a single log entry to database."""
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO auth_logs (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_decision, policy_name, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (log.id, log.timestamp.isoformat(), log.client_mac, log.device_id,
              log.outcome.value, log.vlan_id, log.policy_decision, log.policy_name, log.created_at.isoformat()))
        
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
                INSERT INTO auth_logs (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_decision, policy_name, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (log.id, log.timestamp.isoformat(), log.client_mac, log.device_id,
                  log.outcome.value, log.vlan_id, log.policy_decision, log.policy_name, log.created_at.isoformat()))
        
        conn.commit()
        conn.close()
