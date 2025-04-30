"""Integration tests for the Workflow Orchestrator."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path  # Import Path
from typing import TYPE_CHECKING, Any

import pytest

from orchestrator_mcp_server.ai_client import StubbedAIClient

# Import the implemented components and models
from orchestrator_mcp_server.database import get_db_connection, initialize_database
from orchestrator_mcp_server.definition_service import (
    DefinitionNotFoundError,
    WorkflowDefinitionService,
)
from orchestrator_mcp_server.engine import OrchestrationEngine, OrchestrationEngineError
from orchestrator_mcp_server.models import (
    AdvanceResumeWorkflowOutput,
    ReportPayload,
    StartWorkflowOutput,
    WorkflowInstance,
)
from orchestrator_mcp_server.persistence import (
    InstanceNotFoundError,
    WorkflowPersistenceRepository,
)

if TYPE_CHECKING:
    from collections.abc import Generator

# Define the path to the actual workflows directory for testing parsing
# Adjust this path if your test workflows are in a different location
WORKFLOWS_DIR_FOR_TESTS = Path(__file__).parent.parent.parent / "workflows"  # Use Path


@pytest.fixture
def temp_db_path() -> Generator[str, None, None]:
    """
    Pytest fixture to create a temporary SQLite database file for each test function.

    Ensures the database is initialized and cleaned up afterwards.
    """
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_workflows.sqlite"  # Use Path

        # Set the environment variable for the database path
        os.environ["WORKFLOW_DB_PATH"] = str(
            db_path,
        )  # Convert Path to string for env var

        # Initialize the database schema
        try:
            initialize_database()
        except Exception as e:  # BLE001 # noqa: BLE001
            # TODO: Add logging here # noqa: TD002, TD003, FIX002
            pytest.fail(f"Failed to initialize database: {e}")

        # Yield the database path to the test function
        yield str(db_path)  # Yield as string

        # Teardown: Close connection and cleanup is handled by TemporaryDirectory context manager
        # and the fact that get_db_connection opens/closes connections per call in the repo.
        # Ensure any lingering connections are closed if necessary, though the repo design
        # aims to avoid long-lived connections.
        try:
            # Explicitly close any potential lingering connection from get_db_connection if needed
            # (though the current repo design closes connections after each operation)
            # If using a connection pool or long-lived connection, this would be crucial.
            # For sqlite3 with connections per operation, this might be redundant but safe.
            conn = get_db_connection()
            conn.close()
        except Exception:  # S110, BLE001 # noqa: S110, BLE001
            # TODO: Add logging here # noqa: TD002, TD003, FIX002
            pass  # Ignore errors during cleanup


@pytest.fixture
def workflow_engine(
    temp_db_path: str,
) -> OrchestrationEngine:  # Add temp_db_path dependency
    """
    Pytest fixture to create and configure the OrchestrationEngine for tests.

    Uses the temporary database and stubbed AI client.
    """
    # Ensure the workflows directory exists for the Definition Service
    if not Path(WORKFLOWS_DIR_FOR_TESTS).is_dir():  # Use Path.is_dir()
        pytest.fail(
            f"Workflow definitions directory not found for tests: {WORKFLOWS_DIR_FOR_TESTS}",
        )

    # Instantiate the components
    definition_service = WorkflowDefinitionService(
        str(WORKFLOWS_DIR_FOR_TESTS),
    )  # Pass as string
    persistence_repo = (
        WorkflowPersistenceRepository()
    )  # Uses WORKFLOW_DB_PATH env var set by temp_db_path fixture
    ai_client = StubbedAIClient()  # Use the stubbed client

    # Instantiate the Orchestration Engine
    return OrchestrationEngine(
        definition_service=definition_service,
        persistence_repo=persistence_repo,
        ai_client=ai_client,
    )


# --- Test Cases ---


def test_list_workflows(workflow_engine: OrchestrationEngine) -> None:
    """Test listing available workflows."""
    workflows = workflow_engine.list_workflows()
    # Assert that the list is not empty and contains expected workflow names
    assert isinstance(workflows, list)  # noqa: S101
    assert len(workflows) > 0  # noqa: S101
    # Add more specific assertions based on your actual workflow files
    assert "SPRINT_TASK" in workflows  # noqa: S101
    assert "SAVE" in workflows  # noqa: S101
    assert "RESUME" in workflows  # noqa: S101


def test_start_workflow(workflow_engine: OrchestrationEngine) -> None:
    """Test starting a new workflow instance."""
    # Use the dedicated test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "test_user", "task_id": 123}

    try:
        start_output: StartWorkflowOutput = workflow_engine.start_workflow(
            workflow_name,
            initial_context,
        )

        assert isinstance(start_output, StartWorkflowOutput)  # noqa: S101
        assert isinstance(start_output.instance_id, str)  # noqa: S101
        assert len(start_output.instance_id) > 0  # noqa: S101
        assert start_output.next_step is not None  # noqa: S101
        assert (
            start_output.next_step.get("step_name") == "Start"
        )  # Stubbed AI returns 'Start' # noqa: S101
        assert isinstance(start_output.next_step.get("instructions"), str)  # noqa: S101
        assert (  # noqa: S101
            start_output.current_context == initial_context
        )  # Verify initial context is preserved/merged

        # Verify the instance was created in the database
        instance_from_db = workflow_engine.persistence_repo.get_instance(
            start_output.instance_id,
        )
        assert instance_from_db.instance_id == start_output.instance_id  # noqa: S101
        assert instance_from_db.workflow_name == workflow_name  # noqa: S101
        assert (
            instance_from_db.current_step_name == start_output.next_step["step_name"]
        )  # noqa: S101
        assert instance_from_db.status == "RUNNING"  # noqa: S101
        assert (  # noqa: S101
            instance_from_db.context == initial_context
        )  # Context in DB should match initial context

        # Verify no history entry was created on start (as per architecture)
        history = workflow_engine.persistence_repo.get_history(start_output.instance_id)
        assert len(history) == 0  # noqa: S101

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run start test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_start_workflow: {e}")


def test_advance_workflow_success(workflow_engine: OrchestrationEngine) -> None:
    """Test advancing a workflow instance with a 'success' report."""
    # First, start a workflow instance using the test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "test_user"}
    try:
        start_output = workflow_engine.start_workflow(workflow_name, initial_context)
        instance_id = start_output.instance_id
        first_step_name = start_output.next_step["step_name"]  # Should be 'Start'

        # Now, advance the workflow with a success report for the 'Start' step
        report = ReportPayload(
            step_id=first_step_name,
            result={"status": "completed"},  # Dummy result
            status="success",
            message="Step completed successfully.",
            details=None,
            error=None,
        )
        context_updates = {"step1_data": "some_value"}

        advance_output: AdvanceResumeWorkflowOutput = workflow_engine.advance_workflow(
            instance_id,
            report,
            context_updates,
        )

        assert isinstance(advance_output, AdvanceResumeWorkflowOutput)  # noqa: S101
        assert advance_output.instance_id == instance_id  # noqa: S101
        assert advance_output.next_step is not None  # noqa: S101
        assert (
            advance_output.next_step.get("step_name") == "NextStep"
        )  # Stubbed AI returns 'NextStep' on success # noqa: S101
        assert isinstance(
            advance_output.next_step.get("instructions"), str
        )  # noqa: S101
        # Verify context updates were applied and potentially AI updates (stubbed)
        expected_context = initial_context.copy()
        expected_context.update(context_updates)
        # Stubbed AI might add context, check if it's a superset or matches stub logic
        assert (
            advance_output.current_context.items() >= expected_context.items()
        )  # noqa: S101

        # Verify the instance state was updated in the database
        instance_from_db = workflow_engine.persistence_repo.get_instance(instance_id)
        assert instance_from_db.instance_id == instance_id  # noqa: S101
        assert (  # noqa: S101
            instance_from_db.current_step_name == advance_output.next_step["step_name"]
        )
        assert (  # noqa: S101
            instance_from_db.status == "RUNNING"
        )  # Assuming success doesn't immediately complete
        assert (  # noqa: S101
            instance_from_db.context.items() >= expected_context.items()
        )  # Context in DB should match updated context

        # Verify a history entry was created
        history = workflow_engine.persistence_repo.get_history(instance_id)
        assert len(history) == 1  # noqa: S101
        history_entry = history[0]
        assert history_entry.instance_id == instance_id  # noqa: S101
        assert (  # noqa: S101
            history_entry.step_name == first_step_name
        )  # Should log the step being reported on
        assert history_entry.user_report == report.model_dump()  # noqa: S101
        assert history_entry.outcome_status == "success"  # noqa: S101

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run advance success test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_advance_workflow_success: {e}")


def test_advance_workflow_failure(workflow_engine: OrchestrationEngine) -> None:
    """Test advancing a workflow instance with a 'failure' report."""
    # First, start a workflow instance using the test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "test_user"}
    try:
        start_output = workflow_engine.start_workflow(workflow_name, initial_context)
        instance_id = start_output.instance_id
        first_step_name = start_output.next_step["step_name"]  # Should be 'Start'

        # Now, advance the workflow with a failure report for the 'Start' step
        report = ReportPayload(
            step_id=first_step_name,
            result=None,  # Dummy result
            status="failure",
            message="Step failed.",
            details=None,
            error="Something went wrong.",
        )
        context_updates = {"error_details": "..."}

        advance_output: AdvanceResumeWorkflowOutput = workflow_engine.advance_workflow(
            instance_id,
            report,
            context_updates,
        )

        assert isinstance(advance_output, AdvanceResumeWorkflowOutput)  # noqa: S101
        assert advance_output.instance_id == instance_id  # noqa: S101
        assert advance_output.next_step is not None  # noqa: S101
        # Stubbed AI suggests 'HandleFailure' and status 'FAILED' on failure
        assert (  # noqa: S101
            advance_output.next_step.get("step_name") == "HandleFailure"
        )  # Assuming stub logic
        assert isinstance(
            advance_output.next_step.get("instructions"), str
        )  # noqa: S101
        # Verify context updates were applied
        expected_context = initial_context.copy()
        expected_context.update(context_updates)
        assert (
            advance_output.current_context.items() >= expected_context.items()
        )  # noqa: S101

        # Verify the instance state was updated in the database
        instance_from_db = workflow_engine.persistence_repo.get_instance(instance_id)
        assert instance_from_db.instance_id == instance_id  # noqa: S101
        assert (  # noqa: S101
            instance_from_db.current_step_name == advance_output.next_step["step_name"]
        )
        assert (  # noqa: S101
            instance_from_db.status == "FAILED"
        )  # Assuming stub logic sets status to FAILED
        assert (  # noqa: S101
            instance_from_db.context.items() >= expected_context.items()
        )  # Context in DB should match updated context
        assert (  # noqa: S101
            instance_from_db.completed_at is not None
        )  # Should be marked as completed/failed

        # Verify a history entry was created
        history = workflow_engine.persistence_repo.get_history(instance_id)
        assert len(history) == 1  # noqa: S101
        history_entry = history[0]
        assert history_entry.instance_id == instance_id  # noqa: S101
        assert history_entry.step_name == first_step_name  # noqa: S101
        assert history_entry.user_report == report.model_dump()  # noqa: S101
        assert history_entry.outcome_status == "failure"  # noqa: S101

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run advance failure test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_advance_workflow_failure: {e}")


def test_get_workflow_status(workflow_engine: OrchestrationEngine) -> None:
    """Test retrieving the status of a workflow instance."""
    # First, start a workflow instance using the test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "status_checker"}
    try:
        start_output = workflow_engine.start_workflow(workflow_name, initial_context)
        instance_id = start_output.instance_id

        # Now, get the status
        status_output: WorkflowInstance = workflow_engine.persistence_repo.get_instance(
            instance_id,
        )  # Get directly from repo for simplicity in test

        assert isinstance(  # noqa: S101
            status_output,
            WorkflowInstance,
        )  # Output model is WorkflowInstance
        assert status_output.instance_id == instance_id  # noqa: S101
        assert status_output.workflow_name == workflow_name  # noqa: S101
        assert (
            status_output.current_step_name == start_output.next_step["step_name"]
        )  # noqa: S101
        assert status_output.status == "RUNNING"  # noqa: S101
        assert status_output.context == initial_context  # noqa: S101

        # Test getting status for a non-existent instance
        with pytest.raises(InstanceNotFoundError):
            workflow_engine.persistence_repo.get_instance("non-existent-id")

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run get status test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_get_workflow_status: {e}")


def test_resume_workflow(workflow_engine: OrchestrationEngine) -> None:
    """Test resuming a workflow instance."""
    # First, start a workflow instance using the test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "resumer"}
    try:
        start_output = workflow_engine.start_workflow(workflow_name, initial_context)
        instance_id = start_output.instance_id
        first_step_name = start_output.next_step["step_name"]  # Should be 'Start'

        # Simulate a resume attempt
        assumed_step = (
            first_step_name  # Assume client thinks they are on the first step
        )
        report = ReportPayload(
            step_id=assumed_step,
            result={"current_progress": "half_done"},
            status="resuming",  # Use 'resuming' status for resume report
            message="Resuming workflow.",
            details=None,
            error=None,
        )
        context_updates = {"resume_data": "new_value"}

        resume_output: AdvanceResumeWorkflowOutput = workflow_engine.resume_workflow(
            instance_id,
            assumed_step,
            report,
            context_updates,
        )

        assert isinstance(resume_output, AdvanceResumeWorkflowOutput)  # noqa: S101
        assert resume_output.instance_id == instance_id  # noqa: S101
        assert resume_output.next_step is not None  # noqa: S101
        assert isinstance(resume_output.next_step.get("step_name"), str)  # noqa: S101
        # Stubbed AI reconciliation defaults to persisted step ('Start') in this simple case
        assert resume_output.next_step.get("step_name") == first_step_name  # noqa: S101
        assert isinstance(
            resume_output.next_step.get("instructions"), str
        )  # noqa: S101
        # Verify context updates were applied and potentially AI updates (stubbed reconciliation)
        expected_context = initial_context.copy()
        expected_context.update(context_updates)
        # Stubbed AI reconciliation might add context, check if it's a superset or matches stub logic
        assert (
            resume_output.current_context.items() >= expected_context.items()
        )  # noqa: S101

        # Verify the instance state was updated in the database (should reflect reconciled state)
        instance_from_db = workflow_engine.persistence_repo.get_instance(instance_id)
        assert instance_from_db.instance_id == instance_id  # noqa: S101
        assert (  # noqa: S101
            instance_from_db.current_step_name == resume_output.next_step["step_name"]
        )  # Should be the reconciled step
        assert (  # noqa: S101
            instance_from_db.status == "RUNNING"
        )  # Assuming resume keeps it running unless AI suggests otherwise
        assert (  # noqa: S101
            instance_from_db.context.items() >= expected_context.items()
        )  # Context in DB should match updated context

        # Verify a history entry was created for the resume attempt
        history = workflow_engine.persistence_repo.get_history(instance_id)
        assert len(history) == 1  # noqa: S101
        history_entry = history[0]
        assert history_entry.instance_id == instance_id  # noqa: S101
        assert history_entry.step_name == assumed_step  # noqa: S101
        assert history_entry.user_report == report.model_dump()  # noqa: S101
        assert history_entry.outcome_status == "RESUMING"  # noqa: S101

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run resume test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_resume_workflow: {e}")


def test_workflow_completion(workflow_engine: OrchestrationEngine) -> None:
    """Test advancing a workflow to completion using a 'FINISH' report status."""
    # First, start a workflow instance using the test workflow
    workflow_name = "TEST_INTEGRATION"
    initial_context = {"user": "completer"}
    try:
        start_output = workflow_engine.start_workflow(workflow_name, initial_context)
        instance_id = start_output.instance_id
        current_step_name = start_output.next_step["step_name"]  # Should be 'Start'

        # Now, advance the workflow with a FINISH report status
        report = ReportPayload(
            step_id=current_step_name,  # Report against the step before finishing
            result={"final_output": "done"},
            status="FINISH",  # Use FINISH status to trigger completion via stub
            message="Workflow finished by client report.",
            details=None,
            error=None,
        )
        context_updates = {"final_data": "complete"}

        advance_output: AdvanceResumeWorkflowOutput = workflow_engine.advance_workflow(
            instance_id,
            report,
            context_updates,
        )

        assert isinstance(advance_output, AdvanceResumeWorkflowOutput)  # noqa: S101
        assert advance_output.instance_id == instance_id  # noqa: S101
        assert advance_output.next_step is not None  # noqa: S101
        # Stubbed AI returns 'FINISH' as next step and suggests 'COMPLETED' status
        assert advance_output.next_step.get("step_name") == "FINISH"  # noqa: S101
        assert isinstance(
            advance_output.next_step.get("instructions"), str
        )  # noqa: S101
        # Verify context updates were applied
        expected_context = initial_context.copy()
        expected_context.update(context_updates)
        assert (
            advance_output.current_context.items() >= expected_context.items()
        )  # noqa: S101

        # Verify the instance state was updated to COMPLETED in the database
        instance_from_db = workflow_engine.persistence_repo.get_instance(instance_id)
        assert instance_from_db.instance_id == instance_id  # noqa: S101
        assert instance_from_db.current_step_name == "FINISH"  # noqa: S101
        assert instance_from_db.status == "COMPLETED"  # noqa: S101
        assert (
            instance_from_db.context.items() >= expected_context.items()
        )  # noqa: S101
        assert instance_from_db.completed_at is not None  # noqa: S101

        # Verify a history entry was created for the final step report
        history = workflow_engine.persistence_repo.get_history(instance_id)
        assert len(history) == 1  # noqa: S101
        history_entry = history[0]
        assert history_entry.instance_id == instance_id  # noqa: S101
        assert (
            history_entry.step_name == current_step_name
        )  # Log the step before finish # noqa: S101
        assert history_entry.user_report == report.model_dump()  # noqa: S101
        assert history_entry.outcome_status == "FINISH"  # noqa: S101

    except DefinitionNotFoundError:
        pytest.skip(
            f"Workflow definition '{workflow_name}' not found. Cannot run completion test.",
        )
    except Exception as e:  # BLE001 # noqa: BLE001
        pytest.fail(f"Error during test_workflow_completion: {e}")


def test_advance_non_existent_instance(workflow_engine: OrchestrationEngine) -> None:
    """Test advancing a workflow instance that does not exist."""
    instance_id = "non-existent-instance-id"
    report = ReportPayload(
        step_id="some_step",
        result={},
        status="success",
        message="Attempting to advance non-existent instance.",
        details=None,
        error=None,
    )
    context_updates: dict[str, Any] = {}  # Add type hint

    # Verify that InstanceNotFoundError (or the engine's wrapper) is raised
    # The engine catches InstanceNotFoundError and raises OrchestrationEngineError
    with pytest.raises(OrchestrationEngineError) as excinfo:
        workflow_engine.advance_workflow(instance_id, report, context_updates)

    # Optionally, check the error message or the wrapped exception type
    # Check if the specific message from the engine is present
    assert f"Error processing advance for instance {instance_id}" in str(
        excinfo.value
    )  # noqa: S101
    # Check if the cause was indeed InstanceNotFoundError
    assert isinstance(excinfo.value.__cause__, InstanceNotFoundError)  # noqa: S101
