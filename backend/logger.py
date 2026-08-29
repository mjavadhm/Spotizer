import logging
import logging.handlers
import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Telegram bot token from environment variable for logger
loggertoken = os.getenv('TELEGRAM_LOGGER_TOKEN')

def get_logger(name=None):
    """
    Get a configured logger instance.
    """
    return logging.getLogger(name if name else __name__)

def log_error(message, *args, **kwargs):
    logging.error(message, *args, **kwargs)

def log_info(message, *args, **kwargs):
    logging.info(message, *args, **kwargs)

def log_warning(message, *args, **kwargs):
    logging.warning(message, *args, **kwargs)

def log_debug(message, *args, **kwargs):
    logging.debug(message, *args, **kwargs)
