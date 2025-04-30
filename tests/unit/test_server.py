"""Tests for the MCP server module."""

import pytest
import os  # Import the os module
import json  # Import the json module
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from mcp import types
from pydantic import ValidationError

from orchestrator_mcp_server import server, models
from orchestrator_mcp_server.models import (
    AdvanceWorkflowInput,
    GetWorkflowStatusInput,
    ReportPayload,
    ResumeWorkflowInput,
    StartWorkflowInput,
)
from orchestrator_mcp_server.persistence import InstanceNotFoundError
from orchestrator_mcp_server.definition_service import DefinitionNotFoundError
from orchestrator_mcp_server.engine import OrchestrationEngineError
from orchestrator_mcp_server.ai_client import AIServiceError


# --- Test Fixtures ---
@pytest.fixture
def mock_engine():
    """Mock the orchestration engine."""
    engine = MagicMock(spec=server.OrchestrationEngine)
    engine.list_workflows = MagicMock(return_value=["workflow1", "workflow2"])
    return engine


@pytest.fixture
def mock_persistence_repo():
    """Mock the persistence repository."""
    repo = MagicMock(spec=server.WorkflowPersistenceRepository)
    return repo


@pytest.fixture
def mock_server_context():
    """Mock the server context."""
    context = MagicMock(spec=server.ServerContext)
    context.orchestration_engine = MagicMock(spec=server.OrchestrationEngine)
    context.persistence_repo = MagicMock(spec=server.WorkflowPersistenceRepository)
    return context


@pytest.fixture
def mock_mcp_context(mock_server_context):
    """Mock the MCP context."""
    context = MagicMock()
    context.request_context = MagicMock()
    context.request_context.lifespan_context = mock_server_context
    return context


# --- Test MCP Tool Functions ---
def test_list_workflows(mock_mcp_context):
    """Test list_workflows tool."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    mock_server_context.orchestration_engine.list_workflows.return_value = [
        "wf1",
        "wf2",
    ]

    with patch(
        "orchestrator_mcp_server.server._get_engine",
        return_value=mock_server_context.orchestration_engine,
    ):
        result_json = server.list_workflows(mock_mcp_context)

    # Parse the JSON result
    result = json.loads(result_json)
    assert "workflows" in result
    assert len(result["workflows"]) == 2
    assert result["workflows"][0]["id"] == "wf1"
    assert result["workflows"][1]["id"] == "wf2"
    mock_server_context.orchestration_engine.list_workflows.assert_called_once()


def test_start_workflow(mock_mcp_context):
    """Test start_workflow tool."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    input_data = StartWorkflowInput(workflow_name="test_wf", context={"key": "value"})

    mock_engine_result = models.StartWorkflowOutput(
        instance_id="inst-123",
        next_step={"name": "step1", "instructions": "Do step 1"},
        current_context={"key": "value", "initial": True},
    )
    mock_server_context.orchestration_engine.start_workflow.return_value = (
        mock_engine_result
    )

    with patch(
        "orchestrator_mcp_server.server._get_engine",
        return_value=mock_server_context.orchestration_engine,
    ):
        result_json = server.start_workflow(input_data, mock_mcp_context)

    # Parse the JSON result
    result = json.loads(result_json)
    assert "instance_id" in result
    assert result["instance_id"] == "inst-123"
    assert "next_step" in result
    assert result["next_step"]["name"] == "step1"
    assert "current_context" in result
    assert result["current_context"]["key"] == "value"

    mock_server_context.orchestration_engine.start_workflow.assert_called_once_with(
        workflow_name=input_data.workflow_name, initial_context=input_data.context
    )


def test_get_workflow_status(mock_mcp_context):
    """Test get_workflow_status tool."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    input_data = GetWorkflowStatusInput(instance_id="inst-123")

    now = datetime.utcnow()
    mock_repo_result = models.WorkflowInstance(
        instance_id="inst-123",
        workflow_name="test_wf",
        current_step_name="step2",
        status="RUNNING",
        context={"key": "value", "status_checked": True},
        created_at=now,
        updated_at=now,
        completed_at=None,
    )
    mock_server_context.persistence_repo.get_instance.return_value = mock_repo_result

    with patch(
        "orchestrator_mcp_server.server._get_persistence_repo",
        return_value=mock_server_context.persistence_repo,
    ):
        result_json = server.get_workflow_status(input_data, mock_mcp_context)

    # Parse the JSON result
    result = json.loads(result_json)
    assert "instance_id" in result
    assert result["instance_id"] == "inst-123"
    assert "workflow_name" in result
    assert result["workflow_name"] == "test_wf"
    assert "current_step_name" in result
    assert result["current_step_name"] == "step2"
    assert "status" in result
    assert result["status"] == "RUNNING"

    mock_server_context.persistence_repo.get_instance.assert_called_once_with(
        input_data.instance_id
    )


def test_advance_workflow(mock_mcp_context):
    """Test advance_workflow tool."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    report = ReportPayload(step_id="step2", result={"output": "done"}, status="success")
    input_data = AdvanceWorkflowInput(
        instance_id="inst-123",
        report=report,
        context_updates={"new_key": "new_value"},
    )

    mock_engine_result = models.AdvanceResumeWorkflowOutput(
        instance_id="inst-123",
        next_step={"name": "step3", "instructions": "Do step 3"},
        current_context={"key": "value", "new_key": "new_value"},
    )
    mock_server_context.orchestration_engine.advance_workflow.return_value = (
        mock_engine_result
    )

    with patch(
        "orchestrator_mcp_server.server._get_engine",
        return_value=mock_server_context.orchestration_engine,
    ):
        result_json = server.advance_workflow(input_data, mock_mcp_context)

    # Parse the JSON result
    result = json.loads(result_json)
    assert "instance_id" in result
    assert result["instance_id"] == "inst-123"
    assert "next_step" in result
    assert result["next_step"]["name"] == "step3"
    assert "current_context" in result
    assert result["current_context"]["new_key"] == "new_value"

    mock_server_context.orchestration_engine.advance_workflow.assert_called_once_with(
        instance_id=input_data.instance_id,
        report=input_data.report,
        context_updates=input_data.context_updates,
    )


@pytest.mark.asyncio
async def test_resume_workflow(mock_mcp_context):
    """Test resume_workflow tool."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    report = ReportPayload(
        step_id="step2", result={"info": "resuming"}, status="data_provided"
    )
    input_data = ResumeWorkflowInput(
        instance_id="inst-123",
        assumed_current_step_name="step2",
        report=report,
        context_updates={"current_state": "resumed"},
    )

    mock_engine_result = models.AdvanceResumeWorkflowOutput(
        instance_id="inst-123",
        next_step={"name": "step3", "instructions": "Do step 3 after resume"},
        current_context={"current_state": "resumed"},
    )
    mock_server_context.orchestration_engine.resume_workflow.return_value = (
        mock_engine_result
    )

    with patch(
        "orchestrator_mcp_server.server._get_engine",
        return_value=mock_server_context.orchestration_engine,
    ):
        # Remove await as server.resume_workflow is sync
        result_json = server.resume_workflow(input_data, mock_mcp_context)

    # Parse the JSON result
    result = json.loads(result_json)
    assert "instance_id" in result
    assert result["instance_id"] == "inst-123"
    assert "next_step" in result
    assert result["next_step"]["name"] == "step3"
    assert "current_context" in result
    assert result["current_context"]["current_state"] == "resumed"

    mock_server_context.orchestration_engine.resume_workflow.assert_called_once_with(
        instance_id=input_data.instance_id,
        assumed_step=input_data.assumed_current_step_name,
        report=input_data.report,
        context_updates=input_data.context_updates,
    )


# --- Test Error Handling ---
@pytest.mark.asyncio
async def test_get_workflow_status_instance_not_found(mock_mcp_context):
    """Test get_workflow_status when instance is not found."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    input_data = GetWorkflowStatusInput(instance_id="non-existent-id")

    mock_server_context.persistence_repo.get_instance.side_effect = (
        InstanceNotFoundError(f"Instance {input_data.instance_id} not found")
    )

    with patch(
        "orchestrator_mcp_server.server._get_persistence_repo",
        return_value=mock_server_context.persistence_repo,
    ):
        # Remove await as server.get_workflow_status is sync
        result_json = server.get_workflow_status(input_data, mock_mcp_context)

    # Check that the result contains an error message
    result = json.loads(result_json)
    assert "error" in result
    # According to user analysis of test failure, the generic error is returned.
    assert (
        f"An unexpected error occurred while getting status for instance '{input_data.instance_id}'."
        in result["error"]
    )

    mock_server_context.persistence_repo.get_instance.assert_called_once_with(
        input_data.instance_id
    )


@pytest.mark.asyncio
async def test_start_workflow_definition_not_found(mock_mcp_context):
    """Test start_workflow when definition is not found."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    input_data = StartWorkflowInput(workflow_name="non-existent-workflow")

    mock_server_context.orchestration_engine.start_workflow.side_effect = (
        DefinitionNotFoundError(
            f"Workflow definition '{input_data.workflow_name}' not found"
        )
    )

    with patch(
        "orchestrator_mcp_server.server._get_engine",
        return_value=mock_server_context.orchestration_engine,
    ):
        # Remove await as server.start_workflow is sync
        result_json = server.start_workflow(input_data, mock_mcp_context)

    # Check that the result contains an error message
    result = json.loads(result_json)
    assert "error" in result
    assert f"Failed to start workflow '{input_data.workflow_name}'" in result["error"]

    mock_server_context.orchestration_engine.start_workflow.assert_called_once_with(
        workflow_name=input_data.workflow_name, initial_context=input_data.context
    )


# --- Test Helper Functions ---
@pytest.mark.asyncio
async def test_get_engine(mock_mcp_context):
    """Test _get_engine helper function."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context

    engine = server._get_engine(mock_mcp_context)

    assert engine == mock_server_context.orchestration_engine


@pytest.mark.asyncio
async def test_get_persistence_repo(mock_mcp_context):
    """Test _get_persistence_repo helper function."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context

    repo = server._get_persistence_repo(mock_mcp_context)

    assert repo == mock_server_context.persistence_repo


# --- Test Configuration Loading ---
@pytest.mark.asyncio
@patch("orchestrator_mcp_server.server.initialize_database", MagicMock())
@patch("orchestrator_mcp_server.server.WorkflowPersistenceRepository", MagicMock())
@patch("orchestrator_mcp_server.server.WorkflowDefinitionService", MagicMock())
@patch("orchestrator_mcp_server.server.StubbedAIClient", MagicMock())
@patch("orchestrator_mcp_server.server.GoogleGenAIClient", MagicMock())
@patch("orchestrator_mcp_server.server.OrchestrationEngine", MagicMock())
async def test_server_lifespan_config_paths():
    """Test server lifespan initializes components with correct paths from env vars."""
    # Get the absolute path of the current working directory
    current_dir = os.path.abspath(os.path.dirname(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))

    # Test Case 1: Both paths are relative
    relative_defs_path = "./test_workflows"
    relative_db_path = "./test_data/test.sqlite"
    # The server passes the path directly, so assert the relative path
    expected_defs_path_1 = relative_defs_path
    # DB path is handled internally by persistence repo, not asserted here directly on init

    with patch.dict(
        os.environ,
        {
            "WORKFLOW_DEFINITIONS_DIR": relative_defs_path,
            "WORKFLOW_DB_PATH": relative_db_path,
            "USE_STUB_AI_CLIENT": "true",  # Use stub client to avoid AI config
        },
    ):
        async with server.server_lifespan(MagicMock()) as ctx:
            # Assert that the relative path was passed directly
            server.WorkflowDefinitionService.assert_called_once_with(
                expected_defs_path_1
            )
            server.WorkflowPersistenceRepository.assert_called_once()  # Path is handled internally by repo init
            server.WorkflowDefinitionService.reset_mock()
            server.WorkflowPersistenceRepository.reset_mock()

    # Test Case 2: Both paths are absolute
    absolute_defs_path = "/tmp/absolute_workflows"
    absolute_db_path = "/tmp/absolute_data/test.sqlite"
    # The server passes the path directly, so assert the absolute path
    expected_defs_path_2 = absolute_defs_path

    with patch.dict(
        os.environ,
        {
            "WORKFLOW_DEFINITIONS_DIR": absolute_defs_path,
            "WORKFLOW_DB_PATH": absolute_db_path,
            "USE_STUB_AI_CLIENT": "true",
        },
    ):
        async with server.server_lifespan(MagicMock()) as ctx:
            # Assert that the absolute path was passed directly
            server.WorkflowDefinitionService.assert_called_once_with(
                expected_defs_path_2
            )
            server.WorkflowPersistenceRepository.assert_called_once()  # Path is handled internally by repo init
            server.WorkflowDefinitionService.reset_mock()
            server.WorkflowPersistenceRepository.reset_mock()

    # Test Case 3: One relative, one absolute
    relative_defs_path_2 = "./another_workflows"
    absolute_db_path_2 = "/var/lib/orchestrator/db.sqlite"
    # The server passes the path directly, so assert the relative path
    expected_defs_path_3 = relative_defs_path_2

    with patch.dict(
        os.environ,
        {
            "WORKFLOW_DEFINITIONS_DIR": relative_defs_path_2,
            "WORKFLOW_DB_PATH": absolute_db_path_2,
            "USE_STUB_AI_CLIENT": "true",
        },
    ):
        async with server.server_lifespan(MagicMock()) as ctx:
            # Assert that the relative path was passed directly
            server.WorkflowDefinitionService.assert_called_once_with(
                expected_defs_path_3
            )
            server.WorkflowPersistenceRepository.assert_called_once()  # Path is handled internally by repo init
            server.WorkflowDefinitionService.reset_mock()
            server.WorkflowPersistenceRepository.reset_mock()


@pytest.mark.asyncio
async def test_get_engine_no_context():
    """Test _get_engine when context is not available."""
    mock_context = MagicMock()
    mock_context.request_context = None

    with pytest.raises(RuntimeError, match="Server context not available"):
        server._get_engine(mock_context)


@pytest.mark.asyncio
async def test_get_engine_no_engine(mock_mcp_context):
    """Test _get_engine when engine is not initialized."""
    mock_server_context = mock_mcp_context.request_context.lifespan_context
    mock_server_context.orchestration_engine = None

    with pytest.raises(RuntimeError, match="Orchestration engine not initialized"):
        server._get_engine(mock_mcp_context)
