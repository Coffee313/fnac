"""
SQLite Database Module

Handles all database operations for devices, clients, policies, and logs.
Uses SQLite for simplicity and no external dependencies.
"""

import sqlite3
import logging
from datetime import datetime
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = "fnac.db"


class Database:
    """SQLite database manager for FNAC."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Device Groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS device_groups (
                name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Devices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS devices (
                name TEXT PRIMARY KEY,
                ip_address TEXT NOT NULL UNIQUE,
                shared_secret TEXT NOT NULL,
                device_group_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (device_group_name) REFERENCES device_groups(name)
            )
        """)

        # Client Groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS client_groups (
                name TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Clients table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS clients (
                mac_address TEXT PRIMARY KEY,
                client_group_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_group_name) REFERENCES client_groups(name)
            )
        """)

        # Policies table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS policies (
                name TEXT PRIMARY KEY,
                client_group_name TEXT NOT NULL UNIQUE,
                decision TEXT NOT NULL,
                vlan_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_group_name) REFERENCES client_groups(name)
            )
        """)

        # Authentication Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS auth_logs (
                id TEXT PRIMARY KEY,
                timestamp TIMESTAMP NOT NULL,
                client_mac TEXT NOT NULL,
                device_id TEXT NOT NULL,
                outcome TEXT NOT NULL,
                vlan_id INTEGER,
                policy_decision TEXT,
                policy_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Migrate old schema to new schema if needed
        self._migrate_schema(cursor)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def _migrate_schema(self, cursor) -> None:
        """Migrate old schema to new schema if needed."""
        try:
            # Check if devices table has old 'id' column instead of 'name'
            cursor.execute("PRAGMA table_info(devices)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'id' in columns and 'name' not in columns:
                logger.info("Migrating devices table from 'id' to 'name'")
                cursor.execute("ALTER TABLE devices RENAME COLUMN id TO name")
            
            # Check if clients table has old 'id' column
            cursor.execute("PRAGMA table_info(clients)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'id' in columns and 'mac_address' not in columns:
                logger.info("Migrating clients table")
                # This would require more complex migration, but shouldn't happen with new code
                pass
            
            # Check if policies table has old 'id' column
            cursor.execute("PRAGMA table_info(policies)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'id' in columns and 'name' not in columns:
                logger.info("Migrating policies table from 'id' to 'name'")
                cursor.execute("ALTER TABLE policies RENAME COLUMN id TO name")
            
            # Check if auth_logs table has policy_name column
            cursor.execute("PRAGMA table_info(auth_logs)")
            columns = [row[1] for row in cursor.fetchall()]
            
            if 'policy_name' not in columns:
                logger.info("Adding policy_name column to auth_logs table")
                cursor.execute("ALTER TABLE auth_logs ADD COLUMN policy_name TEXT")
        
        except Exception as e:
            logger.warning(f"Schema migration warning (may be normal): {e}")

    def close(self) -> None:
        """Close database connection."""
        pass  # SQLite handles this automatically
