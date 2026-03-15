import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance for the given module name.
    Logs are output to both Console and logs/system.log with rotation.
    """
    logger = logging.getLogger(name)

    # Avoid duplicate handlers if logger is already configured
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 2. File Handler
    # Ensure logs directory exists at the project root level
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    log_dir = os.path.join(project_root, "logs")
    os.makedirs(log_dir, exist_ok=True)
    
    log_file = os.path.join(log_dir, "system.log")
    
    # Rotate at 5MB, keep 3 backups
    file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger
