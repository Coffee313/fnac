"""
Logging configuration for the RADIUS server application.
"""

import logging
import logging.handlers
import os
from pathlib import Path


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO) -> None:
    """
    Set up logging configuration for the application.
    
    Args:
        log_dir: Directory where log files will be stored
        log_level: Logging level (default: INFO)
    """
    # Create logs directory if it doesn't exist
    Path(log_dir).mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(log_level)
    
    # Create formatters
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = os.path.join(log_dir, 'radius_server.log')
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    logger.info("Logging configured successfully")
