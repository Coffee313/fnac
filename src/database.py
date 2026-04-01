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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {self.db_path}")

    def close(self) -> None:
        """Close database connection."""
        pass  # SQLite handles this automatically
