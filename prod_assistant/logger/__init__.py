# logger/__init__.py

from .custom_logger import CustomLogger
# create a single shared logger instance for the entire application

GLOBAL_LOGGER = CustomLogger().get_logger("prod_assistant")