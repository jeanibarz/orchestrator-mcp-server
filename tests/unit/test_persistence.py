import sqlite3
import pytest
from unittest.mock import MagicMock, patch, call  # Correct import for call

from orchestrator_mcp_server.persistence import (
    WorkflowPersistenceRepository,
    PersistenceError,
    InstanceNotFoundError,
    PersistenceQueryError,
    _raise_instance_not_found,  # Import the helper function if testing directly
)
from orchestrator_mcp_server.models import WorkflowInstance, HistoryEntry

# Define realistic mock data based on models.py structure
# Assuming models have these fields based on persistence code usage
MOCK_INSTANCE_ID = "test-instance-123"
MOCK_WORKFLOW_ID = "test-workflow"
MOCK_STATE = '{"key": "value"}'
MOCK_STEP_ID = "current-step"
MOCK_STATUS = "RUNNING"
MOCK_CONTEXT = '{"context_key": "context_value"}'
MOCK_CREATED_AT = "2023-01-01T10:00:00Z"
MOCK_UPDATED_AT = "2023-01-01T11:00:00Z"

MOCK_HISTORY_ENTRY_ID = 1
MOCK_TIMESTAMP = "2023-01-01T10:30:00Z"
MOCK_HISTORY_STEP_ID = "previous-step"
MOCK_HISTORY_STATUS = "COMPLETED"
MOCK_HISTORY_CONTEXT = '{"history_context": "some_value"}'


@pytest.fixture
def mock_db_connection():
    """Fixture for a mock database connection and cursor."""
    mock_conn = MagicMock(spec=sqlite3.Connection)
    mock_cursor = MagicMock(spec=sqlite3.Cursor)
    mock_conn.cursor.return_value = mock_cursor
    # Make the cursor iterable (for fetchone/fetchall)
    mock_cursor.__iter__.return_value = iter([])  # Default to empty result
    return mock_conn, mock_cursor


@pytest.fixture
def mock_get_db_connection_func(mock_db_connection):
    """Fixture to patch 'get_db_connection'."""
    mock_conn, _ = mock_db_connection
    with patch("orchestrator_mcp_server.persistence.get_db_connection") as mock_get:
        mock_get.return_value = mock_conn
        yield mock_get


@pytest.fixture
def mock_workflow_instance():
    """Fixture for a mock WorkflowInstance object."""
    instance = MagicMock(spec=WorkflowInstance)
    instance.instance_id = MOCK_INSTANCE_ID
    instance.workflow_id = MOCK_WORKFLOW_ID
    instance.current_state_json = MOCK_STATE
    instance.current_step_id = MOCK_STEP_ID
    instance.status = MOCK_STATUS
    instance.context_json = MOCK_CONTEXT
    instance.created_at = MOCK_CREATED_AT
    instance.updated_at = MOCK_UPDATED_AT

    # Mock the to_db_row method to return a COPY each time
    # This prevents modifications in tests affecting subsequent calls within the SUT
    db_row_data = {
        "instance_id": MOCK_INSTANCE_ID,
        "workflow_id": MOCK_WORKFLOW_ID,
        "current_state_json": MOCK_STATE,
        "current_step_id": MOCK_STEP_ID,
        "status": MOCK_STATUS,
        "context_json": MOCK_CONTEXT,
        "created_at": MOCK_CREATED_AT,  # Included but popped in update
        "updated_at": MOCK_UPDATED_AT,  # Included but popped in update
        "history_entry_id": None,  # Included but popped
    }
    instance.to_db_row.side_effect = lambda: db_row_data.copy()
    return instance


@pytest.fixture
def mock_history_entry():
    """Fixture for a mock HistoryEntry object."""
    entry = MagicMock(spec=HistoryEntry)
    entry.history_entry_id = MOCK_HISTORY_ENTRY_ID
    entry.instance_id = MOCK_INSTANCE_ID
    entry.timestamp = MOCK_TIMESTAMP
    entry.step_id = MOCK_HISTORY_STEP_ID
    entry.status = MOCK_HISTORY_STATUS
    entry.context_json = MOCK_HISTORY_CONTEXT

    entry.to_db_row.return_value = {
        "history_entry_id": MOCK_HISTORY_ENTRY_ID,  # Included but popped
        "instance_id": MOCK_INSTANCE_ID,
        "timestamp": MOCK_TIMESTAMP,
        "step_id": MOCK_HISTORY_STEP_ID,
        "status": MOCK_HISTORY_STATUS,
        "context_json": MOCK_HISTORY_CONTEXT,
    }
    return entry


@pytest.fixture
def repository(mock_get_db_connection_func):
    """Fixture for the WorkflowPersistenceRepository with mocked connection."""
    # The patch is already active via mock_get_db_connection_func fixture
    return WorkflowPersistenceRepository()


# --- Test _raise_instance_not_found ---
# Covers lines 34-35


def test_raise_instance_not_found():
    """Test that _raise_instance_not_found raises InstanceNotFoundError."""
    message = "Specific test message"
    with pytest.raises(InstanceNotFoundError, match=message):
        _raise_instance_not_found(message)


# --- Tests for WorkflowPersistenceRepository ---


class TestWorkflowPersistenceRepository:

    # --- create_instance tests ---
    # Covers lines 43-66 (happy path) and 68-77 (error paths)

    def test_create_instance_success(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test successful creation of a workflow instance."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance

        # Expected data after popping 'history_entry_id'
        expected_data_dict = instance_data.to_db_row()
        expected_data_dict.pop("history_entry_id", None)
        expected_columns = ", ".join(expected_data_dict.keys())
        expected_placeholders = ", ".join("?" * len(expected_data_dict))
        expected_sql = f"INSERT INTO workflow_instances ({expected_columns}) VALUES ({expected_placeholders})"
        expected_values = list(expected_data_dict.values())

        repository.create_instance(instance_data)

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(expected_sql, expected_values)
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_create_instance_sqlite_error(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test handling of sqlite3.Error during instance creation."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance
        original_error = sqlite3.Error("DB write error")
        mock_cursor.execute.side_effect = original_error

        with pytest.raises(PersistenceQueryError) as excinfo:
            repository.create_instance(instance_data)

        assert f"Failed to create workflow instance {instance_data.instance_id}" in str(
            excinfo.value
        )
        assert excinfo.value.original_error is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()  # Check it was called
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_called_once()  # Should rollback on error
        mock_conn.close.assert_called_once()

    def test_create_instance_unexpected_error(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test handling of unexpected Exception during instance creation."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance
        original_error = ValueError("Unexpected issue")
        # Simulate error during data processing before execute
        mock_workflow_instance.to_db_row.side_effect = original_error

        with pytest.raises(PersistenceError) as excinfo:
            repository.create_instance(instance_data)

        assert "An unexpected error occurred during instance creation" in str(
            excinfo.value
        )
        assert (
            excinfo.value.__cause__ is original_error
        )  # Check if original error is chained

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()  # Cursor IS called before to_db_row
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_not_called()  # Rollback only on sqlite3.Error
        mock_conn.close.assert_called_once()  # Finally block should still close

    # --- get_instance tests ---
    # Covers lines 82-94 (happy path), 91-93 (not found), 95-97 (sqlite error), 98-101 (unexpected error), 102-105 (finally)

    def test_get_instance_success(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test successful retrieval of a workflow instance."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        # Simulate a row returned from the database
        # Need to create a structure that dict() can convert, like a tuple or a mock row factory
        mock_row_data = {
            "instance_id": MOCK_INSTANCE_ID,
            "workflow_id": MOCK_WORKFLOW_ID,
            "current_state_json": MOCK_STATE,
            "current_step_id": MOCK_STEP_ID,
            "status": MOCK_STATUS,
            "context_json": MOCK_CONTEXT,
            "created_at": MOCK_CREATED_AT,
            "updated_at": MOCK_UPDATED_AT,
        }
        # Mock sqlite3.Row behavior for dict(row)
        mock_row = MagicMock(spec=sqlite3.Row)
        mock_row.keys.return_value = list(mock_row_data.keys())
        # Make the mock row subscriptable like a tuple/dict
        mock_row.__getitem__.side_effect = lambda key: (
            mock_row_data[mock_row.keys()[key]]
            if isinstance(key, int)
            else mock_row_data[key]
        )

        mock_cursor.fetchone.return_value = mock_row

        # Mock the class method WorkflowInstance.from_db_row
        with patch(
            "orchestrator_mcp_server.persistence.WorkflowInstance.from_db_row"
        ) as mock_from_db:
            mock_result_instance = MagicMock(spec=WorkflowInstance)
            mock_from_db.return_value = mock_result_instance

            result = repository.get_instance(instance_id)

            mock_get_db_connection_func.assert_called_once()
            mock_conn.cursor.assert_called_once()
            expected_sql = "SELECT * FROM workflow_instances WHERE instance_id = ?"
            mock_cursor.execute.assert_called_once_with(expected_sql, (instance_id,))
            mock_cursor.fetchone.assert_called_once()
            mock_from_db.assert_called_once_with(
                mock_row_data
            )  # Ensure dict(row) worked
            assert result is mock_result_instance
            mock_conn.close.assert_called_once()

    def test_get_instance_not_found(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test retrieval when instance is not found."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = "non-existent-id"
        mock_cursor.fetchone.return_value = None  # Simulate no row found

        with pytest.raises(
            InstanceNotFoundError,
            match=f"Workflow instance with ID {instance_id} not found.",
        ):
            repository.get_instance(instance_id)

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        expected_sql = "SELECT * FROM workflow_instances WHERE instance_id = ?"
        mock_cursor.execute.assert_called_once_with(expected_sql, (instance_id,))
        mock_cursor.fetchone.assert_called_once()
        mock_conn.close.assert_called_once()  # Finally block

    def test_get_instance_sqlite_error(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test handling of sqlite3.Error during instance retrieval."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        original_error = sqlite3.Error("DB read error")
        mock_cursor.execute.side_effect = original_error

        with pytest.raises(PersistenceQueryError) as excinfo:
            repository.get_instance(instance_id)

        assert f"Failed to retrieve workflow instance {instance_id}" in str(
            excinfo.value
        )
        assert excinfo.value.original_error is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchone.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_get_instance_unexpected_error(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test handling of unexpected Exception during instance retrieval."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        original_error = TypeError("Unexpected data type in row")

        # Simulate error during row processing after fetchone
        mock_row = MagicMock(spec=sqlite3.Row)  # Simulate a row was found
        mock_cursor.fetchone.return_value = mock_row
        # Mock from_db_row to raise the error
        with patch(
            "orchestrator_mcp_server.persistence.WorkflowInstance.from_db_row"
        ) as mock_from_db:
            mock_from_db.side_effect = original_error

            with pytest.raises(PersistenceError) as excinfo:
                repository.get_instance(instance_id)

            assert "An unexpected error occurred during instance retrieval" in str(
                excinfo.value
            )
            assert excinfo.value.__cause__ is original_error

            mock_get_db_connection_func.assert_called_once()
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchone.assert_called_once()
            mock_from_db.assert_called_once()  # Check it was called
            mock_conn.close.assert_called_once()

    # --- update_instance tests ---
    # Covers lines 112-134

    def test_update_instance_success(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test successful update of a workflow instance."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance

        # Expected data after popping keys
        expected_data_dict = instance_data.to_db_row()
        instance_id = expected_data_dict.pop("instance_id")
        expected_data_dict.pop("history_entry_id", None)
        expected_data_dict.pop("created_at", None)
        expected_data_dict.pop("updated_at", None)

        expected_set_clauses = ", ".join([f"{key} = ?" for key in expected_data_dict])
        expected_sql = f"UPDATE workflow_instances SET {expected_set_clauses} WHERE instance_id = ?"
        expected_values = [*list(expected_data_dict.values()), instance_id]

        repository.update_instance(instance_data)

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(expected_sql, expected_values)
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_update_instance_sqlite_error(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test handling of sqlite3.Error during instance update."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance
        original_error = sqlite3.Error("DB update error")
        mock_cursor.execute.side_effect = original_error

        with pytest.raises(PersistenceQueryError) as excinfo:
            repository.update_instance(instance_data)

        assert f"Failed to update workflow instance {instance_data.instance_id}" in str(
            excinfo.value
        )
        assert excinfo.value.original_error is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_update_instance_unexpected_error(
        self,
        repository,
        mock_db_connection,
        mock_workflow_instance,
        mock_get_db_connection_func,
    ):
        """Test handling of unexpected Exception during instance update."""
        mock_conn, mock_cursor = mock_db_connection
        instance_data = mock_workflow_instance
        original_error = AttributeError("Missing attribute")
        # Simulate error during data prep
        mock_workflow_instance.to_db_row.side_effect = original_error

        with pytest.raises(PersistenceError) as excinfo:
            repository.update_instance(instance_data)

        assert "An unexpected error occurred during instance update" in str(
            excinfo.value
        )
        assert excinfo.value.__cause__ is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()  # Cursor IS called before to_db_row
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    # --- create_history_entry tests ---
    # Covers lines 146-168

    def test_create_history_entry_success(
        self,
        repository,
        mock_db_connection,
        mock_history_entry,
        mock_get_db_connection_func,
    ):
        """Test successful creation of a history entry."""
        mock_conn, mock_cursor = mock_db_connection
        history_data = mock_history_entry

        expected_data_dict = history_data.to_db_row()
        expected_data_dict.pop("history_entry_id", None)
        expected_columns = ", ".join(expected_data_dict.keys())
        expected_placeholders = ", ".join("?" * len(expected_data_dict))
        expected_sql = f"INSERT INTO workflow_history ({expected_columns}) VALUES ({expected_placeholders})"
        expected_values = list(expected_data_dict.values())

        repository.create_history_entry(history_data)

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with(expected_sql, expected_values)
        mock_conn.commit.assert_called_once()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_create_history_entry_sqlite_error(
        self,
        repository,
        mock_db_connection,
        mock_history_entry,
        mock_get_db_connection_func,
    ):
        """Test handling of sqlite3.Error during history entry creation."""
        mock_conn, mock_cursor = mock_db_connection
        history_data = mock_history_entry
        original_error = sqlite3.Error("DB history write error")
        mock_cursor.execute.side_effect = original_error

        with pytest.raises(PersistenceQueryError) as excinfo:
            repository.create_history_entry(history_data)

        assert (
            f"Failed to create history entry for instance {history_data.instance_id}"
            in str(excinfo.value)
        )
        assert excinfo.value.original_error is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_called_once()
        mock_conn.close.assert_called_once()

    def test_create_history_entry_unexpected_error(
        self,
        repository,
        mock_db_connection,
        mock_history_entry,
        mock_get_db_connection_func,
    ):
        """Test handling of unexpected Exception during history entry creation."""
        mock_conn, mock_cursor = mock_db_connection
        history_data = mock_history_entry
        original_error = KeyError("Missing key in data")
        # Simulate error during data prep
        mock_history_entry.to_db_row.side_effect = original_error

        with pytest.raises(PersistenceError) as excinfo:
            repository.create_history_entry(history_data)

        assert "An unexpected error occurred during history entry creation" in str(
            excinfo.value
        )
        assert excinfo.value.__cause__ is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()  # Cursor IS called before to_db_row
        mock_conn.commit.assert_not_called()
        mock_conn.rollback.assert_not_called()
        mock_conn.close.assert_called_once()

    # --- get_history tests ---
    # Covers lines 178-200

    def test_get_history_success_no_limit(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test successful retrieval of history entries without a limit."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID

        # Simulate multiple rows returned
        mock_row_data_1 = {
            "history_entry_id": 1,
            "instance_id": instance_id,
            "step_id": "step1",
            "status": "OK",
            "timestamp": "T1",
            "context_json": "{}",
        }
        mock_row_data_2 = {
            "history_entry_id": 2,
            "instance_id": instance_id,
            "step_id": "step2",
            "status": "OK",
            "timestamp": "T2",
            "context_json": "{}",
        }

        # Mock sqlite3.Row behavior
        mock_row_1 = MagicMock(spec=sqlite3.Row)
        mock_row_1.keys.return_value = list(mock_row_data_1.keys())
        mock_row_1.__getitem__.side_effect = lambda k: (
            mock_row_data_1[mock_row_1.keys()[k]]
            if isinstance(k, int)
            else mock_row_data_1[k]
        )
        mock_row_2 = MagicMock(spec=sqlite3.Row)
        mock_row_2.keys.return_value = list(mock_row_data_2.keys())
        mock_row_2.__getitem__.side_effect = lambda k: (
            mock_row_data_2[mock_row_2.keys()[k]]
            if isinstance(k, int)
            else mock_row_data_2[k]
        )

        mock_cursor.fetchall.return_value = [mock_row_1, mock_row_2]

        # Mock the class method HistoryEntry.from_db_row
        with patch(
            "orchestrator_mcp_server.persistence.HistoryEntry.from_db_row"
        ) as mock_from_db:
            mock_entry_1 = MagicMock(spec=HistoryEntry)
            mock_entry_2 = MagicMock(spec=HistoryEntry)
            mock_from_db.side_effect = [
                mock_entry_1,
                mock_entry_2,
            ]  # Return different mocks for each call

            results = repository.get_history(instance_id)

            mock_get_db_connection_func.assert_called_once()
            mock_conn.cursor.assert_called_once()
            expected_sql = "SELECT * FROM workflow_history WHERE instance_id = ? ORDER BY timestamp ASC"
            mock_cursor.execute.assert_called_once_with(
                expected_sql, [instance_id]
            )  # Params as list
            mock_cursor.fetchall.assert_called_once()
            # Check from_db_row calls
            assert mock_from_db.call_count == 2
            mock_from_db.assert_has_calls(
                [call(mock_row_data_1), call(mock_row_data_2)]
            )
            assert results == [mock_entry_1, mock_entry_2]
            mock_conn.close.assert_called_once()

    def test_get_history_success_with_limit(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test successful retrieval of history entries with a limit."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        limit = 5

        mock_cursor.fetchall.return_value = (
            []
        )  # Assume empty for simplicity, focus on SQL

        # Mock the class method HistoryEntry.from_db_row
        with patch(
            "orchestrator_mcp_server.persistence.HistoryEntry.from_db_row"
        ) as mock_from_db:
            results = repository.get_history(instance_id, limit=limit)

            mock_get_db_connection_func.assert_called_once()
            mock_conn.cursor.assert_called_once()
            expected_sql = "SELECT * FROM workflow_history WHERE instance_id = ? ORDER BY timestamp ASC LIMIT ?"
            expected_params = [instance_id, limit]  # Params as list
            mock_cursor.execute.assert_called_once_with(expected_sql, expected_params)
            mock_cursor.fetchall.assert_called_once()
            mock_from_db.assert_not_called()  # No rows returned
            assert results == []
            mock_conn.close.assert_called_once()

    def test_get_history_sqlite_error(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test handling of sqlite3.Error during history retrieval."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        original_error = sqlite3.Error("DB history read error")
        mock_cursor.execute.side_effect = original_error

        with pytest.raises(PersistenceQueryError) as excinfo:
            repository.get_history(instance_id)

        assert f"Failed to retrieve history for instance {instance_id}" in str(
            excinfo.value
        )
        assert excinfo.value.original_error is original_error

        mock_get_db_connection_func.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.fetchall.assert_not_called()
        mock_conn.close.assert_called_once()

    def test_get_history_unexpected_error(
        self, repository, mock_db_connection, mock_get_db_connection_func
    ):
        """Test handling of unexpected Exception during history retrieval."""
        mock_conn, mock_cursor = mock_db_connection
        instance_id = MOCK_INSTANCE_ID
        original_error = ValueError("Bad data in history row")

        # Simulate error during row processing after fetchall
        mock_row = MagicMock(spec=sqlite3.Row)  # Simulate rows were found
        mock_cursor.fetchall.return_value = [mock_row]
        # Mock from_db_row to raise the error
        with patch(
            "orchestrator_mcp_server.persistence.HistoryEntry.from_db_row"
        ) as mock_from_db:
            mock_from_db.side_effect = original_error

            with pytest.raises(PersistenceError) as excinfo:
                repository.get_history(instance_id)

            assert "An unexpected error occurred during history retrieval" in str(
                excinfo.value
            )
            assert excinfo.value.__cause__ is original_error

            mock_get_db_connection_func.assert_called_once()
            mock_conn.cursor.assert_called_once()
            mock_cursor.execute.assert_called_once()
            mock_cursor.fetchall.assert_called_once()
            mock_from_db.assert_called_once()  # Check it was called
            mock_conn.close.assert_called_once()
