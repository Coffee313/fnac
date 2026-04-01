"""
Main entry point for the RADIUS server application.
"""

import logging
import sys
import threading
import time
from pathlib import Path

from src.logging_config import setup_logging
from src.device_manager import Device_Manager
from src.client_manager import Client_Manager
from src.policy_engine import Policy_Engine
from src.log_manager import Log_Manager
from src.freeradius_config_generator import FreeRADIUSConfigGenerator
from src.freeradius_log_parser import FreeRADIUSLogParser
from src.api import create_app
from src.migrate_json_to_db import migrate_all


def _log_parser_thread(log_parser: FreeRADIUSLogParser) -> None:
    """Background thread that periodically parses FreeRADIUS logs."""
    logger = logging.getLogger(__name__)
    while True:
        try:
            new_entries = log_parser.parse_logs()
            if new_entries > 0:
                logger.debug(f"Parsed {new_entries} new FreeRADIUS log entries")
        except Exception as e:
            logger.error(f"Error in log parser thread: {e}")
        
        # Check for new logs every 2 seconds
        time.sleep(2)


def main() -> int:
    """
    Initialize and start the RADIUS server.
    
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Set up logging
        setup_logging()
        logger = logging.getLogger(__name__)
        
        logger.info("Starting RADIUS server...")
        
        # Run migration from JSON to database
        logger.info("Checking for data migration...")
        migrate_all()
        
        # Initialize managers
        device_manager = Device_Manager()
        client_manager = Client_Manager()
        policy_engine = Policy_Engine()
        log_manager = Log_Manager()
        
        logger.info("Managers initialized")
        
        # Create FreeRADIUS config generator
        config_generator = FreeRADIUSConfigGenerator(
            device_manager=device_manager,
            client_manager=client_manager,
            policy_engine=policy_engine,
        )
        logger.info("FreeRADIUS config generator initialized")
        
        # Create FreeRADIUS log parser
        log_parser = FreeRADIUSLogParser(log_manager)
        logger.info("FreeRADIUS log parser initialized")
        
        # Create Flask app
        app = create_app(
            device_manager,
            client_manager,
            policy_engine,
            log_manager,
            config_generator=config_generator,
        )
        logger.info("Flask app created")
        
        # Note: RADIUS server is now handled by FreeRADIUS (UDP 1812)
        # FNAC is a management UI only
        logger.info("FNAC is a management UI for FreeRADIUS")
        logger.info("FreeRADIUS handles RADIUS protocol on UDP 1812")
        
        # Start FreeRADIUS log parser in a background thread
        parser_thread = threading.Thread(
            target=_log_parser_thread,
            args=(log_parser,),
            daemon=True
        )
        parser_thread.start()
        logger.info("FreeRADIUS log parser started")
        
        # Start Flask in a thread
        flask_thread = threading.Thread(
            target=lambda: app.run(host='0.0.0.0', port=5000, debug=False),
            daemon=True
        )
        flask_thread.start()
        logger.info("Flask server started on port 5000")
        
        logger.info("RADIUS server initialized successfully")
        
        # Keep the main thread alive
        try:
            while True:
                threading.Event().wait(1)
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            return 0
        
    except Exception as e:
        logging.error(f"Failed to initialize RADIUS server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
