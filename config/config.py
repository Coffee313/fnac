"""
Configuration settings for the RADIUS server application.
"""

import os
from pathlib import Path


# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = os.getenv("RADIUS_DATA_DIR", str(BASE_DIR / "data"))
LOG_DIR = os.getenv("RADIUS_LOG_DIR", str(BASE_DIR / "logs"))

# RADIUS server settings
RADIUS_PORT = int(os.getenv("RADIUS_PORT", 1812))
RADIUS_LISTEN_ADDRESS = os.getenv("RADIUS_LISTEN_ADDRESS", "0.0.0.0")

# Flask settings
FLASK_HOST = os.getenv("FLASK_HOST", "127.0.0.1")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Logging settings
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Persistence settings
PERSISTENCE_FORMAT = "json"  # Currently only JSON is supported
DEVICES_FILE = os.path.join(DATA_DIR, "devices.json")
CLIENTS_FILE = os.path.join(DATA_DIR, "clients.json")
POLICIES_FILE = os.path.join(DATA_DIR, "policies.json")
LOGS_FILE = os.path.join(DATA_DIR, "logs.json")

# Create data directory if it doesn't exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
