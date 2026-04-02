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

    def _optimize_sqlite(self, cursor) -> None:
        """Optimize SQLite for high throughput."""
        try:
            # Write-Ahead Logging for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            
            # Faster writes (acceptable for most use cases)
            cursor.execute("PRAGMA synchronous=NORMAL")
            
            # Larger cache for better performance
            cursor.execute("PRAGMA cache_size=10000")
            
            # Use memory for temp storage
            cursor.execute("PRAGMA temp_store=MEMORY")
            
            # Memory-mapped I/O for faster access
            cursor.execute("PRAGMA mmap_size=30000000000")
            
            # Increase timeout for lock contention
            cursor.execute("PRAGMA busy_timeout=5000")
            
            logger.info("SQLite optimizations applied")
        except Exception as e:
            logger.warning(f"Could not apply SQLite optimizations: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Initialize database schema."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Optimize SQLite for high throughput
        self._optimize_sqlite(cursor)

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
                name TEXT DEFAULT '',
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
            # Check if devices table has old 'device_group_id' instead of 'device_group_name'
            cursor.execute("PRAGMA table_info(devices)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if 'device_group_id' in columns and 'device_group_name' not in columns:
                logger.info("Migrating devices table from 'device_group_id' to 'device_group_name'")
                cursor.execute("ALTER TABLE devices RENAME COLUMN device_group_id TO device_group_name")
            
            if 'id' in columns and 'name' not in columns:
                logger.info("Migrating devices table from 'id' to 'name'")
                cursor.execute("ALTER TABLE devices RENAME COLUMN id TO name")
            
            # Check if clients table has old 'client_group_id' instead of 'client_group_name'
            cursor.execute("PRAGMA table_info(clients)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if 'client_group_id' in columns and 'client_group_name' not in columns:
                logger.info("Migrating clients table from 'client_group_id' to 'client_group_name'")
                cursor.execute("ALTER TABLE clients RENAME COLUMN client_group_id TO client_group_name")
            
            if 'name' not in columns:
                logger.info("Adding name column to clients table")
                cursor.execute("ALTER TABLE clients ADD COLUMN name TEXT DEFAULT ''")
            
            # Check if policies table has old 'id' column
            cursor.execute("PRAGMA table_info(policies)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if 'id' in columns and 'name' not in columns:
                logger.info("Migrating policies table from 'id' to 'name'")
                cursor.execute("ALTER TABLE policies RENAME COLUMN id TO name")
            
            # Check if policies table has old 'client_group_id' instead of 'client_group_name'
            if 'client_group_id' in columns and 'client_group_name' not in columns:
                logger.info("Migrating policies table from 'client_group_id' to 'client_group_name'")
                cursor.execute("ALTER TABLE policies RENAME COLUMN client_group_id TO client_group_name")
            
            # Check if auth_logs table has policy_name column
            cursor.execute("PRAGMA table_info(auth_logs)")
            columns = {row[1]: row for row in cursor.fetchall()}
            
            if 'policy_name' not in columns:
                logger.info("Adding policy_name column to auth_logs table")
                cursor.execute("ALTER TABLE auth_logs ADD COLUMN policy_name TEXT")
        
        except Exception as e:
            logger.warning(f"Schema migration: {e}")

    def close(self) -> None:
        """Close database connection."""
        pass  # SQLite handles this automatically
