import logging
import logging.handlers
import os
import requests
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Get Telegram bot token from environment variable for security
loggertoken = os.getenv('TELEGRAM_LOGGER_TOKEN')

# Basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(filename)s:%(lineno)d - %(message)s',
    handlers=[
        logging.handlers.RotatingFileHandler('app.log', maxBytes=1048576, backupCount=3),
        # logging.FileHandler('app.log')
        logging.StreamHandler()
    ]
)


def send_error_to_external_service(log_entry):
    """Send error logs to a Telegram channel."""
    try:
        url = f"https://api.telegram.org/bot{loggertoken}/sendMessage"
        data = {
            'chat_id': -1002218658979,
            'text': log_entry
        }
        response = requests.post(url, data=data)
    except Exception as e:
        logging.error(f"Failed to send error log to Telegram: {str(e)}")


def send_info_to_external_service(log_entry):
    """Send info logs to a different Telegram channel."""
    try:
        url = f"https://api.telegram.org/bot{loggertoken}/sendMessage"
        data = {
            'chat_id': -1002410804323,
            'text': log_entry
        }
        response = requests.post(url, data=data)
    except Exception as e:
        logging.error(f"Failed to send info log to Telegram: {str(e)}")


class CustomHandler(logging.Handler):
    """Custom logging handler to forward logs to external services."""
    def __init__(self):
        super().__init__()
        # Create a formatter for log messages that includes timestamp and context info
        self.formatter = logging.Formatter('%(levelname)s - %(message)s - %(asctime)s - %(name)s - %(module)s - %(funcName)s - %(filename)s:%(lineno)d')

    def emit(self, record):
        """Process the log record and send to appropriate external service."""
        log_entry = self.format(record)

        if record.levelname == 'ERROR':
            if "message can't be forwarded" not in log_entry:
                send_error_to_external_service(log_entry)
        # Uncomment to enable INFO level forwarding
        elif record.levelname == 'INFO':
            send_info_to_external_service(log_entry)


# Create and add the custom handler
custom_handler = CustomHandler()

# Get a logger for the current module
logger = logging.getLogger(__name__)
logger.addHandler(custom_handler)


# Utility functions for easy access in other modules
def get_logger(name=None):
    """
    Get a configured logger instance.
    
    Args:
        name: The name for the logger (typically __name__ from the calling module)
        
    Returns:
        A configured logger instance
    """
    module_logger = logging.getLogger(name if name else __name__)
    module_logger.addHandler(custom_handler)
    return module_logger


def log_error(message, *args, **kwargs):
    """Convenience function to log errors."""
    logger.error(message, *args, **kwargs)


def log_info(message, *args, **kwargs):
    """Convenience function to log info messages."""
    logger.info(message, *args, **kwargs)


def log_warning(message, *args, **kwargs):
    """Convenience function to log warnings."""
    logger.warning(message, *args, **kwargs)


def log_debug(message, *args, **kwargs):
    """Convenience function to log debug messages."""
    logger.debug(message, *args, **kwargs)