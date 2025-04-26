"""Unit tests for the AI Client module."""

import json
from unittest.mock import MagicMock, Mock, patch

import pytest
from typing_extensions import Any

from orchestrator_mcp_server.ai_client import (
    GoogleGenAIClient,
    StubbedAIClient,
    _raise_ai_invalid_response,
)
from orchestrator_mcp_server.models import (
    AIInvalidResponseError,
    AIResponse,
    AIServiceAPIError,
    AIServiceError,
    AIServiceTimeoutError,
    AISafetyError,
    HistoryEntry,
    WorkflowInstance,
)

# Constants for testing
TEST_DEFINITION_BLOB = """
Workflow: TestWorkflow
Steps:
  - name: Start
    description: Initial step.
    Orchestrator Guidance: Move to StepA.
  - name: StepA
    description: Step A.
    Orchestrator Guidance: If report status is 'success', move to StepB. If 'failure', move to HandleFailure.
  - name: StepB
    description: Step B.
    Orchestrator Guidance: Finish workflow.
  - name: HandleFailure
    description: Handles failures.
    Orchestrator Guidance: Set status to FAILED and finish.
  - name: AskForClarification
    description: Ask user for more info.
    Orchestrator Guidance: Wait for report with status 'data_provided', then move to ProcessClarification.
  - name: ProcessClarification
    description: Process the clarified data.
    Orchestrator Guidance: Move to StepB.
"""


# --- Fixtures ---


@pytest.fixture
def stubbed_client() -> StubbedAIClient:
    """Fixture for StubbedAIClient."""
    return StubbedAIClient()


@pytest.fixture
def mock_workflow_instance() -> WorkflowInstance:
    """Fixture for a mock WorkflowInstance."""
    return WorkflowInstance(
        instance_id="wf_123",
        workflow_name="TestWorkflow",
        current_step_name="StepA",
        context={"key1": "value1"},
        status="RUNNING",
    )


@pytest.fixture
def mock_persisted_state() -> WorkflowInstance:
    """Fixture for a mock persisted WorkflowInstance for resume tests."""
    return WorkflowInstance(
        instance_id="wf_resume_456",
        workflow_name="TestResumeWorkflow",
        current_step_name="AskForClarification",
        context={"persisted_key": "persisted_value"},
        status="SUSPENDED",
    )


@pytest.fixture
def mock_history(mock_workflow_instance: WorkflowInstance) -> list[HistoryEntry]:
    """Fixture for mock history entries."""
    instance_id = mock_workflow_instance.instance_id
    return [
        HistoryEntry(
            instance_id=instance_id,
            step_name="Start",
            outcome_status="success",
            user_report={"status": "success"},
            timestamp="2023-01-01T10:00:00Z",
        ),
        HistoryEntry(
            instance_id=instance_id,
            step_name="StepA",
            outcome_status="pending",
            user_report={"status": "pending"},
            timestamp="2023-01-01T10:05:00Z",
        ),
    ]


# --- Tests for StubbedAIClient ---


def test_stubbed_determine_first_step(stubbed_client: StubbedAIClient):
    """Test StubbedAIClient.determine_first_step."""
    response = stubbed_client.determine_first_step("definition")
    assert isinstance(response, AIResponse)
    assert response.next_step_name == "Start"
    assert response.reasoning == "Stubbed: Returning 'Start' as the first step."
    assert response.updated_context == {}
    assert response.status_suggestion is None


def test_stubbed_determine_next_step_success(
    stubbed_client: StubbedAIClient, mock_workflow_instance: WorkflowInstance
):
    """Test StubbedAIClient.determine_next_step with success report."""
    report = {"status": "success"}
    response = stubbed_client.determine_next_step(
        "definition", mock_workflow_instance, report, None
    )
    assert response.next_step_name == "NextStep"
    assert response.reasoning is not None
    assert "Report status was 'success'" in response.reasoning
    assert response.updated_context == {}
    assert response.status_suggestion is None


def test_stubbed_determine_next_step_failure(
    stubbed_client: StubbedAIClient, mock_workflow_instance: WorkflowInstance
):
    """Test StubbedAIClient.determine_next_step with failure report."""
    report = {"status": "failure"}
    response = stubbed_client.determine_next_step(
        "definition", mock_workflow_instance, report, None
    )
    assert response.next_step_name == "HandleFailure"
    assert response.reasoning is not None
    assert "Report status was 'failure'" in response.reasoning
    assert response.updated_context == {}
    assert response.status_suggestion == "FAILED"


def test_stubbed_determine_next_step_finish(
    stubbed_client: StubbedAIClient, mock_workflow_instance: WorkflowInstance
):
    """Test StubbedAIClient.determine_next_step with FINISH report."""
    report = {"status": "FINISH"}
    response = stubbed_client.determine_next_step(
        "definition", mock_workflow_instance, report, None
    )
    assert response.next_step_name == "FINISH"
    assert response.reasoning is not None
    assert "Report status was 'FINISH'" in response.reasoning
    assert response.updated_context == {}
    assert response.status_suggestion == "COMPLETED"


def test_stubbed_determine_next_step_clarification(stubbed_client: StubbedAIClient):
    """Test StubbedAIClient.determine_next_step with clarification logic."""
    clarification_instance = WorkflowInstance(
        instance_id="wf_clarify",
        workflow_name="TestClarifyWorkflow",
        current_step_name="AskForClarification",
        context={},
        status="SUSPENDED",
    )
    report = {"status": "data_provided", "details": {"info": "extra data"}}
    response = stubbed_client.determine_next_step(
        "definition", clarification_instance, report, None
    )
    assert response.next_step_name == "ProcessClarification"
    assert response.reasoning is not None
    assert "Received data after clarification request" in response.reasoning
    assert "Merging report details into context" in response.reasoning
    assert response.updated_context == {"info": "extra data"}
    assert response.status_suggestion is None


def test_stubbed_determine_next_step_other(
    stubbed_client: StubbedAIClient, mock_workflow_instance: WorkflowInstance
):
    """Test StubbedAIClient.determine_next_step with other report status."""
    report = {"status": "other_status"}
    response = stubbed_client.determine_next_step(
        "definition", mock_workflow_instance, report, None
    )
    assert response.next_step_name == "NextStep"
    assert response.reasoning is not None
    assert "Report status was 'other_status'" in response.reasoning
    assert response.updated_context == {}
    assert response.status_suggestion is None


def test_stubbed_reconcile_next_step_finish(
    stubbed_client: StubbedAIClient, mock_persisted_state: WorkflowInstance
):
    """Test StubbedAIClient.reconcile_and_determine_next_step with FINISH report."""
    report = {"status": "FINISH"}
    assumed_step = "SomeStep"
    response = stubbed_client.reconcile_and_determine_next_step(
        "definition", mock_persisted_state, assumed_step, report, None
    )
    assert response.next_step_name == "FINISH"
    assert response.reasoning is not None
    assert "Report status was 'FINISH'" in response.reasoning
    assert response.status_suggestion == "COMPLETED"


def test_stubbed_reconcile_next_step_failure(
    stubbed_client: StubbedAIClient, mock_persisted_state: WorkflowInstance
):
    """Test StubbedAIClient.reconcile_and_determine_next_step with failure report."""
    report = {"status": "failure"}
    assumed_step = "SomeStep"
    response = stubbed_client.reconcile_and_determine_next_step(
        "definition", mock_persisted_state, assumed_step, report, None
    )
    assert response.next_step_name == "HandleFailure"
    assert response.reasoning is not None
    assert "Report status was 'failure'" in response.reasoning
    assert response.status_suggestion == "FAILED"


def test_stubbed_reconcile_next_step_success(
    stubbed_client: StubbedAIClient, mock_persisted_state: WorkflowInstance
):
    """Test StubbedAIClient.reconcile_and_determine_next_step with success report."""
    report = {"status": "success"}
    assumed_step = "SomeStep"
    response = stubbed_client.reconcile_and_determine_next_step(
        "definition", mock_persisted_state, assumed_step, report, None
    )
    assert response.next_step_name == "NextStep"
    assert response.reasoning is not None
    assert "Report status was 'success' during resume" in response.reasoning


def test_stubbed_reconcile_next_step_context_update(
    stubbed_client: StubbedAIClient, mock_persisted_state: WorkflowInstance
):
    """Test StubbedAIClient.reconcile_and_determine_next_step with context updates in report."""
    report = {"status": "resuming", "context_updates": {"new_key": "new_value"}}
    assumed_step = mock_persisted_state.current_step_name
    response = stubbed_client.reconcile_and_determine_next_step(
        "definition", mock_persisted_state, assumed_step, report, None
    )
    assert response.reasoning is not None
    assert "Merging report context_updates into context" in response.reasoning
    assert response.updated_context == {"new_key": "new_value"}
    assert response.status_suggestion == mock_persisted_state.status


def test_stubbed_reconcile_next_step_persisted_none(stubbed_client: StubbedAIClient):
    """Test StubbedAIClient.reconcile_and_determine_next_step when persisted step is None."""
    persisted_state_none = WorkflowInstance(
        instance_id="wf_none",
        workflow_name="TestNoneWorkflow",
        current_step_name=None,
        context={},
        status="PENDING",
    )
    report = {"status": "starting"}
    assumed_step = "Start"
    response = stubbed_client.reconcile_and_determine_next_step(
        "definition", persisted_state_none, assumed_step, report, None
    )
    assert response.next_step_name == "Start"
    assert response.reasoning is not None
    assert "Defaulting to 'Start' (persisted step was None)" in response.reasoning


# --- Tests for Helper Functions ---


def test_raise_ai_invalid_response():
    """Test _raise_ai_invalid_response helper."""
    message = "Invalid stuff"
    raw_response = '{"bad": "json"'
    with pytest.raises(AIInvalidResponseError, match=message) as exc_info:
        _raise_ai_invalid_response(message, raw_response=raw_response)
    assert exc_info.value.raw_response == raw_response


# --- Tests for GoogleGenAIClient ---


@patch("orchestrator_mcp_server.ai_client.genai")
def test_google_genai_client_init(mock_genai):
    """Test GoogleGenAIClient initialization."""
    api_key = "test-api-key"
    model_name = "test-model"
    timeout = 30

    client = GoogleGenAIClient(
        api_key=api_key, model_name=model_name, request_timeout_seconds=timeout
    )

    mock_genai.configure.assert_called_once_with(api_key=api_key)
    mock_genai.GenerativeModel.assert_called_once_with(model_name)
    assert client.request_timeout_seconds == timeout
    assert client.model_name == model_name


@patch("orchestrator_mcp_server.ai_client.genai")
def test_google_genai_client_init_from_env(mock_genai, monkeypatch):
    """Test GoogleGenAIClient initialization from environment variable."""
    env_api_key = "env-api-key"
    monkeypatch.setenv("GEMINI_API_KEY", env_api_key)

    client = GoogleGenAIClient()

    mock_genai.configure.assert_called_once_with(api_key=env_api_key)
    mock_genai.GenerativeModel.assert_called_once()


@patch("orchestrator_mcp_server.ai_client.genai")
def test_google_genai_client_init_missing_api_key(mock_genai, monkeypatch):
    """Test GoogleGenAIClient initialization with missing API key."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    with pytest.raises(ValueError, match="GEMINI_API_KEY not provided"):
        GoogleGenAIClient()


@patch("orchestrator_mcp_server.ai_client.GoogleGenAIClient._call_gemini_api")
@patch("orchestrator_mcp_server.ai_client.GoogleGenAIClient._build_prompt")
@patch("orchestrator_mcp_server.ai_client.GoogleGenAIClient._generate_response_schema")
def test_google_genai_determine_next_step(
    mock_generate_schema,
    mock_build_prompt,
    mock_call_api,
    mock_workflow_instance,
    mock_history,
):
    """Test GoogleGenAIClient.determine_next_step."""
    # Setup mocks
    mock_prompt = "test prompt"
    mock_build_prompt.return_value = mock_prompt

    mock_schema = {"type": "OBJECT", "properties": {}}
    mock_generate_schema.return_value = mock_schema

    mock_api_response = {
        "next_step_name": "StepB",
        "updated_context": [{"key": "test_key", "value": "test_value"}],
        "status_suggestion": "RUNNING",
        "reasoning": "Test reasoning",
    }
    mock_call_api.return_value = mock_api_response

    # Create client with mocked dependencies
    client = GoogleGenAIClient(api_key="test-key")

    # Test the method
    report = {"status": "success"}
    result = client.determine_next_step(
        TEST_DEFINITION_BLOB, mock_workflow_instance, report, mock_history
    )

    # Verify results
    mock_build_prompt.assert_called_once()
    mock_generate_schema.assert_called_once_with(TEST_DEFINITION_BLOB)
    mock_call_api.assert_called_once_with(mock_prompt, schema=mock_schema)

    assert isinstance(result, AIResponse)
    assert result.next_step_name == "StepB"
    assert result.updated_context == {"test_key": "test_value"}
    assert result.status_suggestion == "RUNNING"
    assert result.reasoning == "Test reasoning"
