"""Handles SQLite database connection, initialization, and basic setup."""

import os
import sqlite3
from pathlib import Path

# Removed module-level DATABASE_PATH definition


def get_db_connection() -> sqlite3.Connection:
    """Establish and return a connection to the SQLite database."""
    # Determine database path dynamically inside the function
    database_path = Path(os.environ.get("WORKFLOW_DB_PATH", "./data/workflows.sqlite"))

    # Ensure the directory for the database file exists
    db_dir = database_path.parent
    # Use mkdir with parents=True and exist_ok=True to simplify directory creation
    db_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row  # Access columns by name
    return conn


def initialize_database() -> None:
    """Create the necessary tables and triggers if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    create_instances_table_sql = """
        CREATE TABLE IF NOT EXISTS workflow_instances (
            instance_id TEXT PRIMARY KEY,
            workflow_name TEXT NOT NULL,
            current_step_name TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('RUNNING', 'SUSPENDED', 'COMPLETED', 'FAILED')),
            context TEXT, -- Stored as JSON string
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME NOT NULL,
            completed_at DATETIME DEFAULT NULL
        );
    """

    create_history_table_sql = """
        CREATE TABLE IF NOT EXISTS workflow_history (
            history_entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            instance_id TEXT NOT NULL,
            timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            step_name TEXT NOT NULL,
            user_report TEXT, -- Stored as JSON string
            outcome_status TEXT,
            determined_next_step TEXT,
            FOREIGN KEY (instance_id) REFERENCES workflow_instances (instance_id) ON DELETE CASCADE
        );
    """

    create_updated_at_trigger_sql = """
        CREATE TRIGGER IF NOT EXISTS trigger_workflow_instances_updated_at
        AFTER UPDATE ON workflow_instances
        FOR EACH ROW
        BEGIN
            UPDATE workflow_instances SET updated_at = CURRENT_TIMESTAMP WHERE instance_id = OLD.instance_id;
        END;
    """

    create_history_index_sql = """
        CREATE INDEX IF NOT EXISTS idx_workflow_history_instance_id ON workflow_history (instance_id);
    """

    try:
        cursor.execute(create_instances_table_sql)
        cursor.execute(create_history_table_sql)
        cursor.execute(create_updated_at_trigger_sql)
        cursor.execute(create_history_index_sql)
        conn.commit()
    except sqlite3.Error:
        conn.rollback()
        raise  # Re-raise the exception
    finally:
        conn.close()


# Example usage for direct script execution (e.g., initial setup)
if __name__ == "__main__":
    # T201 Fix: Removed print statement
    initialize_database()
    # T201 Fix: Removed print statement
    # Example connection test
    try:
        conn_test = get_db_connection()
        # T201 Fix: Removed print statement
        conn_test.close()
    except sqlite3.Error:  # F841 Fix: Remove unused 'as e'
        # T201 Fix: Removed print statement
        pass  # Keep the block structure, maybe add logging later if needed
