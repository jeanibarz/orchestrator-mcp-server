"""Persistence layer for handling workflow state in the database."""

import sqlite3
from typing import Any

from .database import get_db_connection
from .models import HistoryEntry, WorkflowInstance  # Import the defined models


# Define custom exceptions for persistence errors as per Section 6.4
class PersistenceError(Exception):
    """Base exception for persistence-related errors."""


class InstanceNotFoundError(PersistenceError):
    """Exception raised when a workflow instance is not found."""


class PersistenceConnectionError(PersistenceError):
    """Exception raised for database connection errors."""


class PersistenceQueryError(PersistenceError):
    """Exception raised for database query execution errors."""

    def __init__(self, message: str, original_error: sqlite3.Error) -> None:
        """
        Initialize PersistenceQueryError.

        Args:
            message: The error message.
            original_error: The original sqlite3.Error that occurred.

        """
        super().__init__(message)
        self.original_error = original_error


def _raise_instance_not_found(message: str) -> None:
    """Raise an InstanceNotFoundError."""
    raise InstanceNotFoundError(message)


class WorkflowPersistenceRepository:
    """
    Repository class for managing workflow instance and history persistence in SQLite.

    Implements the conceptual AbstractPersistenceRepository interface.
    """

    def create_instance(self, instance_data: WorkflowInstance) -> None:
        """Create a new workflow instance record in the database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Use the to_db_row method from the model
            data = instance_data.to_db_row()
            # Remove history_entry_id as it's not part of instance data
            data.pop("history_entry_id", None)

            # Construct the INSERT query dynamically from the dictionary keys
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            sql = f"INSERT INTO workflow_instances ({columns}) VALUES ({placeholders})"  # noqa: S608 - Column names from trusted model

            cursor.execute(sql, list(data.values()))
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            msg = f"Failed to create workflow instance {instance_data.instance_id}"
            raise PersistenceQueryError(msg, e) from e  # B904: Add from e
        except Exception as e:
            msg = f"An unexpected error occurred during instance creation: {e}"
            raise PersistenceError(msg) from e  # B904/BLE001: Add from e
        finally:
            if conn:
                conn.close()

    def get_instance(self, instance_id: str) -> WorkflowInstance:
        """Retrieve a workflow instance record by its ID."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "SELECT * FROM workflow_instances WHERE instance_id = ?"
            cursor.execute(sql, (instance_id,))
            row = cursor.fetchone()

            if row is None:
                _raise_instance_not_found(
                    f"Workflow instance with ID {instance_id} not found.",
                )

            # Use the from_db_row method from the model
            return WorkflowInstance.from_db_row(dict(row))

        except sqlite3.Error as e:
            msg = f"Failed to retrieve workflow instance {instance_id}"
            raise PersistenceQueryError(msg, e) from e  # B904: Add from e
        except InstanceNotFoundError:
            raise  # Re-raise the specific not found error
        except Exception as e:
            msg = f"An unexpected error occurred during instance retrieval: {e}"
            raise PersistenceError(msg) from e  # B904/BLE001: Add from e
        finally:
            if conn:
                conn.close()

    def update_instance(self, instance_data: WorkflowInstance) -> None:
        """Update an existing workflow instance record."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Use the to_db_row method from the model
            data = instance_data.to_db_row()
            instance_id = data.pop("instance_id")  # Get instance_id for WHERE clause
            # Remove history_entry_id as it's not part of instance data
            data.pop("history_entry_id", None)
            # Remove created_at as it should not be updated
            data.pop("created_at", None)
            # Remove updated_at as it's handled by the trigger
            data.pop("updated_at", None)

            # Construct the UPDATE query dynamically
            set_clauses = ", ".join([f"{key} = ?" for key in data])
            sql = f"UPDATE workflow_instances SET {set_clauses} WHERE instance_id = ?"  # noqa: S608 - Column names from trusted model

            cursor.execute(sql, [*list(data.values()), instance_id])
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            msg = f"Failed to update workflow instance {instance_data.instance_id}"
            raise PersistenceQueryError(msg, e) from e  # B904: Add from e
        except Exception as e:
            msg = f"An unexpected error occurred during instance update: {e}"
            raise PersistenceError(msg) from e  # B904/BLE001: Add from e
        finally:
            if conn:
                conn.close()

    def create_history_entry(self, history_data: HistoryEntry) -> None:
        """Create a new history entry record in the database."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            # Use the to_db_row method from the model
            data = history_data.to_db_row()
            # Remove history_entry_id as it's auto-incremented
            data.pop("history_entry_id", None)

            # Construct the INSERT query dynamically
            columns = ", ".join(data.keys())
            placeholders = ", ".join("?" * len(data))
            sql = f"INSERT INTO workflow_history ({columns}) VALUES ({placeholders})"  # noqa: S608 - Column names from trusted model

            cursor.execute(sql, list(data.values()))
            conn.commit()
        except sqlite3.Error as e:
            if conn:
                conn.rollback()
            msg = f"Failed to create history entry for instance {history_data.instance_id}"
            raise PersistenceQueryError(msg, e) from e  # B904: Add from e
        except Exception as e:
            msg = f"An unexpected error occurred during history entry creation: {e}"
            raise PersistenceError(msg) from e  # B904/BLE001: Add from e
        finally:
            if conn:
                conn.close()

    def get_history(
        self,
        instance_id: str,
        limit: int | None = None,
    ) -> list[HistoryEntry]:
        """Retrieve history entries for a workflow instance, optionally limited."""
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            sql = "SELECT * FROM workflow_history WHERE instance_id = ? ORDER BY timestamp ASC"
            params: list[Any] = [instance_id]

            if limit is not None and limit > 0:
                sql += " LIMIT ?"
                params.append(limit)  # Keep limit as int for execute

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # Convert rows to HistoryEntry models
            return [HistoryEntry.from_db_row(dict(row)) for row in rows]

        except sqlite3.Error as e:
            msg = f"Failed to retrieve history for instance {instance_id}"
            raise PersistenceQueryError(msg, e) from e  # B904: Add from e
        except Exception as e:
            msg = f"An unexpected error occurred during history retrieval: {e}"
            raise PersistenceError(msg) from e  # B904/BLE001: Add from e
        finally:
            if conn:
                conn.close()
