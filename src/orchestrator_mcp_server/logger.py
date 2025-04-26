import logging
import os
import pathlib

# Define default log directory and ensure it exists
LOG_DIR = os.environ.get("ORCHESTRATOR_LOG_DIR", "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# Define the log file paths with environment variable overrides
ORCHESTRATOR_LOG_FILE = os.environ.get(
    "ORCHESTRATOR_LOG_FILE", os.path.join(LOG_DIR, "orchestrator.log")
)

AI_INTERACTIONS_LOG_FILE = os.environ.get(
    "AI_INTERACTIONS_LOG_FILE", os.path.join(LOG_DIR, "ai_interactions.log")
)


def setup_logger(log_file=None):
    """
    Configures the root logger to output to a file and the console.

    Args:
        log_file: Optional specific log file path to use. If None, uses ORCHESTRATOR_LOG_FILE.
    """
    # Use the specified log file or default to ORCHESTRATOR_LOG_FILE
    log_file = log_file or ORCHESTRATOR_LOG_FILE

    # Get the root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)  # Set a base logging level

    # Create a file handler
    # Use 'a' mode to append to the file if it exists
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.INFO)  # Set level for file output

    # Create a console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)  # Set level for console output

    # Create a formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Add formatter to handlers
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers to the logger
    # Prevent adding duplicate handlers if setup_logger is called multiple times
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Log a message to indicate logger setup
    logger.info("Logger configured. Logging to %s", os.path.abspath(log_file))


# Call setup_logger when the module is imported
setup_logger()

# You can get specific loggers in other modules like this:
# from .logger import setup_logger
# import logging
# logger = logging.getLogger(__name__)
# setup_logger() # Call setup_logger once at the application entry point
