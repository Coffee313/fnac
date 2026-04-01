"""
Migration script to import data from JSON files to SQLite database.

Run this once to migrate existing JSON data to the new database.
"""

import json
import logging
from pathlib import Path
from datetime import datetime

from src.database import Database
from src.models import Device, DeviceGroup, Client, ClientGroup, MABPolicy, AuthenticationLog, PolicyDecision, AuthenticationOutcome

logger = logging.getLogger(__name__)

# Old JSON file paths
DATA_DIR = Path("data")
DEVICES_FILE = DATA_DIR / "devices.json"
CLIENTS_FILE = DATA_DIR / "clients.json"
POLICIES_FILE = DATA_DIR / "policies.json"
LOGS_FILE = DATA_DIR / "logs.json"


def migrate_devices() -> int:
    """Migrate devices from JSON to database."""
    if not DEVICES_FILE.exists():
        logger.info("No devices.json file found, skipping device migration")
        return 0
    
    try:
        with open(DEVICES_FILE) as f:
            data = json.load(f)
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for device_data in data.get("devices", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO devices (id, ip_address, shared_secret, device_group_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    device_data['id'],
                    device_data['ip_address'],
                    device_data['shared_secret'],
                    device_data['device_group_id'],
                    device_data.get('created_at', datetime.utcnow().isoformat()),
                    device_data.get('updated_at', datetime.utcnow().isoformat()),
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate device {device_data.get('id')}: {e}")
        
        for group_data in data.get("groups", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO device_groups (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    group_data['id'],
                    group_data['name'],
                    group_data.get('created_at', datetime.utcnow().isoformat()),
                    group_data.get('updated_at', datetime.utcnow().isoformat()),
                ))
            except Exception as e:
                logger.warning(f"Failed to migrate device group {group_data.get('id')}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Migrated {count} devices")
        return count
    
    except Exception as e:
        logger.error(f"Error migrating devices: {e}")
        return 0


def migrate_clients() -> int:
    """Migrate clients from JSON to database."""
    if not CLIENTS_FILE.exists():
        logger.info("No clients.json file found, skipping client migration")
        return 0
    
    try:
        with open(CLIENTS_FILE) as f:
            data = json.load(f)
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for group_data in data.get("groups", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO client_groups (id, name, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    group_data['id'],
                    group_data['name'],
                    group_data.get('created_at', datetime.utcnow().isoformat()),
                    group_data.get('updated_at', datetime.utcnow().isoformat()),
                ))
            except Exception as e:
                logger.warning(f"Failed to migrate client group {group_data.get('id')}: {e}")
        
        for client_data in data.get("clients", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO clients (mac_address, client_group_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    client_data['mac_address'],
                    client_data['client_group_id'],
                    client_data.get('created_at', datetime.utcnow().isoformat()),
                    client_data.get('updated_at', datetime.utcnow().isoformat()),
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate client {client_data.get('mac_address')}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Migrated {count} clients")
        return count
    
    except Exception as e:
        logger.error(f"Error migrating clients: {e}")
        return 0


def migrate_policies() -> int:
    """Migrate policies from JSON to database."""
    if not POLICIES_FILE.exists():
        logger.info("No policies.json file found, skipping policy migration")
        return 0
    
    try:
        with open(POLICIES_FILE) as f:
            data = json.load(f)
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for policy_data in data.get("policies", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO policies (id, client_group_id, decision, vlan_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    policy_data['id'],
                    policy_data['client_group_id'],
                    policy_data['decision'],
                    policy_data.get('vlan_id'),
                    policy_data.get('created_at', datetime.utcnow().isoformat()),
                    policy_data.get('updated_at', datetime.utcnow().isoformat()),
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate policy {policy_data.get('id')}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Migrated {count} policies")
        return count
    
    except Exception as e:
        logger.error(f"Error migrating policies: {e}")
        return 0


def migrate_logs() -> int:
    """Migrate logs from JSON to database."""
    if not LOGS_FILE.exists():
        logger.info("No logs.json file found, skipping log migration")
        return 0
    
    try:
        with open(LOGS_FILE) as f:
            data = json.load(f)
        
        db = Database()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        count = 0
        for log_data in data.get("logs", []):
            try:
                cursor.execute("""
                    INSERT OR IGNORE INTO auth_logs (id, timestamp, client_mac, device_id, outcome, vlan_id, policy_decision, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    log_data['id'],
                    log_data['timestamp'],
                    log_data['client_mac'],
                    log_data['device_id'],
                    log_data['outcome'],
                    log_data.get('vlan_id'),
                    log_data.get('policy_decision'),
                    log_data.get('created_at', datetime.utcnow().isoformat()),
                ))
                count += 1
            except Exception as e:
                logger.warning(f"Failed to migrate log {log_data.get('id')}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Migrated {count} logs")
        return count
    
    except Exception as e:
        logger.error(f"Error migrating logs: {e}")
        return 0


def migrate_all() -> None:
    """Run all migrations."""
    logger.info("Starting JSON to SQLite migration...")
    
    device_count = migrate_devices()
    client_count = migrate_clients()
    policy_count = migrate_policies()
    log_count = migrate_logs()
    
    logger.info(f"Migration complete: {device_count} devices, {client_count} clients, {policy_count} policies, {log_count} logs")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    migrate_all()
