"""
Main entry point for the RADIUS server application.
"""

import logging
import sys
import threading
from pathlib import Path

from src.logging_config import setup_logging
from src.device_manager import Device_Manager
from src.client_manager import Client_Manager
from src.policy_engine import Policy_Engine
from src.log_manager import Log_Manager
from src.api import create_app


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
        
        # Initialize managers
        device_manager = Device_Manager()
        client_manager = Client_Manager()
        policy_engine = Policy_Engine()
        log_manager = Log_Manager()
        
        logger.info("Managers initialized")
        
        # Create Flask app
        app = create_app(device_manager, client_manager, policy_engine, log_manager)
        logger.info("Flask app created")
        
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
