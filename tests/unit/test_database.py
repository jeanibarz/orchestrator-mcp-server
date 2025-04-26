import sys
import os

# Add the project root directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

import sqlite3
import pytest
from pathlib import Path

# Assuming the module structure allows direct import
# If not, we might need to adjust sys.path or use a different import method
from src.orchestrator_mcp_server.database import initialize_database, get_db_connection


# Use pytest fixture for temporary directory
def test_initialize_database_creates_file_and_tables(tmp_path):
    """
    Test that initialize_database creates the database file and necessary tables
    when the file does not exist.
    """
    # Construct a temporary database path within the pytest temporary directory
    temp_db_path = tmp_path / "test_workflows.sqlite"

    # Ensure the environment variable points to the temporary path for this test
    # Use pytest's monkeypatch fixture for safe environment variable modification
    original_db_path = os.environ.get("WORKFLOW_DB_PATH")
    os.environ["WORKFLOW_DB_PATH"] = str(temp_db_path)

    try:
        # Call the function to initialize the database
        initialize_database()

        # Assert that the database file was created
        assert temp_db_path.exists()

        # Connect to the newly created database and verify tables
        conn = sqlite3.connect(temp_db_path)
        cursor = conn.cursor()

        # Check if the workflow_instances table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_instances';"
        )
        instance_table = cursor.fetchone()
        assert instance_table is not None, "workflow_instances table was not created"

        # Check if the workflow_history table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='workflow_history';"
        )
        history_table = cursor.fetchone()
        assert history_table is not None, "workflow_history table was not created"

        # Check if the trigger exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='trigger' AND name='trigger_workflow_instances_updated_at';"
        )
        trigger = cursor.fetchone()
        assert (
            trigger is not None
        ), "trigger_workflow_instances_updated_at trigger was not created"

        # Check if the index exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_workflow_history_instance_id';"
        )
        index = cursor.fetchone()
        assert (
            index is not None
        ), "idx_workflow_history_instance_id index was not created"

        conn.close()

    finally:
        # Clean up the environment variable
        if original_db_path is None:
            del os.environ["WORKFLOW_DB_PATH"]
        else:
            os.environ["WORKFLOW_DB_PATH"] = original_db_path


# Note: This test assumes that the necessary dependencies (like pytest) are installed
# and that the module can be imported correctly based on the project structure.
