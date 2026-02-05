"""
Utility functions and decorators
"""

import asyncio
import logging
import re
from functools import wraps
from pathlib import Path
from typing import Any

from . import config


def retry(max_attempts: int = config.MAX_RETRY_ATTEMPTS,
          delay: float = config.RETRY_DELAY):
    """
    Decorator to retry async functions on failure

    Args:
        max_attempts: Maximum number of retry attempts
        delay: Delay in seconds between retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts - 1:
                        raise

                    # Get logger if available from args
                    logger = None
                    if args and hasattr(args[0], 'logger'):
                        logger = args[0].logger

                    if logger:
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. Retrying..."
                        )

                    await asyncio.sleep(delay)
            return None
        return wrapper
    return decorator


def sanitize_filename(name: str, max_length: int = config.MAX_FILENAME_LENGTH) -> str:
    """
    Sanitize string for use in filename

    Args:
        name: String to sanitize
        max_length: Maximum length of resulting filename

    Returns:
        Sanitized filename string
    """
    # Remove/replace invalid characters
    name = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces and hyphens with underscores
    name = re.sub(r'[-\s]+', '_', name)
    # Limit length
    return name[:max_length]


def setup_directories(*directories: Path) -> None:
    """
    Create directories if they don't exist

    Args:
        *directories: Variable number of Path objects to create
    """
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def setup_logging(log_dir: Path, log_level: str = 'INFO') -> logging.Logger:
    """
    Setup logging configuration

    Args:
        log_dir: Directory for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger('DashboardScraper')
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('[%(levelname)s] %(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'scraper.log')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


def count_data_points(tables: list) -> int:
    """
    Count total data points from extracted tables

    Args:
        tables: List of table dictionaries

    Returns:
        Total number of data points (rows across all tables)
    """
    return sum(len(table.get('rows', [])) for table in tables)
