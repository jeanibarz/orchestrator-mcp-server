import os
import logging
import unittest
from unittest.mock import patch
import tempfile
import shutil

from orchestrator_mcp_server.logger import setup_logger, LOG_DIR, ORCHESTRATOR_LOG_FILE


class TestLogger(unittest.TestCase):
    """Test cases for the logger module."""

    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for logs during tests
        self.test_log_dir = tempfile.mkdtemp()
        self.original_log_dir = LOG_DIR

        # Clear any existing handlers from the root logger
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    def tearDown(self):
        """Clean up after tests."""
        # Remove the temporary directory
        shutil.rmtree(self.test_log_dir, ignore_errors=True)

        # Clear any handlers added during tests
        logger = logging.getLogger()
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

    @patch("orchestrator_mcp_server.logger.LOG_DIR")
    def test_setup_logger_creates_log_file(self, mock_log_dir):
        """Test that setup_logger creates the log file in the specified directory."""
        # Set the mock log directory to our temporary directory
        mock_log_dir.return_value = self.test_log_dir

        # Call setup_logger with a specific log file path in our test directory
        test_log_file = os.path.join(self.test_log_dir, "test_orchestrator.log")
        setup_logger(test_log_file)

        # Get a logger and log a test message
        logger = logging.getLogger("test_logger")
        logger.info("Test log message")

        # Check that the log file was created
        self.assertTrue(
            os.path.exists(test_log_file), f"Log file {test_log_file} was not created"
        )

        # Check that the log file contains our test message
        with open(test_log_file, "r") as f:
            log_content = f.read()
            self.assertIn("Test log message", log_content)

    def test_environment_variable_override(self):
        """Test that environment variables can override log file paths."""
        # This test would normally use environment variables, but for unit testing
        # we can directly check the code logic that uses os.environ.get()
        with patch.dict("os.environ", {"ORCHESTRATOR_LOG_DIR": self.test_log_dir}):
            # Re-import the module to trigger the environment variable check
            import importlib
            import orchestrator_mcp_server.logger

            importlib.reload(orchestrator_mcp_server.logger)

            # Check that LOG_DIR was set from the environment variable
            self.assertEqual(orchestrator_mcp_server.logger.LOG_DIR, self.test_log_dir)


if __name__ == "__main__":
    unittest.main()
