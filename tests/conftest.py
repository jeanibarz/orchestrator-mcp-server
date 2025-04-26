"""
Global pytest fixtures and configuration.
"""

import os
import sys
import pytest
from unittest.mock import MagicMock, patch

# Set environment variables needed for testing
os.environ["USE_STUB_AI_CLIENT"] = "true"
os.environ["GEMINI_MODEL_NAME"] = "gemini-test-model"
os.environ["WORKFLOW_DEFINITIONS_DIR"] = "./workflows"
os.environ["WORKFLOW_DB_PATH"] = ":memory:"

# Add mocks for external dependencies that might not be installed
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["google.api_core"] = MagicMock()
sys.modules["google.api_core.exceptions"] = MagicMock()
sys.modules["google.generativeai.types"] = MagicMock()


# Mock classes for google.generativeai.types
class MockGenerateContentResponse:
    def __init__(self, text=""):
        self.text = text
        self.prompt_feedback = MagicMock()
        self.prompt_feedback.block_reason = None


sys.modules["google.generativeai.types"].GenerateContentResponse = (
    MockGenerateContentResponse
)
sys.modules["google.generativeai.types"].GenerationConfig = MagicMock
sys.modules["google.generativeai.types"].RequestOptionsType = MagicMock


# Create fixtures that can be used across test files
@pytest.fixture
def mock_workflow_instance():
    """Fixture for a mock workflow instance."""
    from orchestrator_mcp_server.models import WorkflowInstance
    from datetime import datetime

    return WorkflowInstance(
        instance_id="test-instance-id",
        workflow_name="test-workflow",
        current_step_name="test-step",
        status="RUNNING",
        context={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        completed_at=None,
    )


@pytest.fixture
def mock_report():
    """Fixture for a mock report."""
    return {
        "step_id": "test-step",
        "result": {"output": "test-output"},
        "status": "success",
    }


@pytest.fixture
def mock_history_entry():
    """Fixture for a mock history entry."""
    from orchestrator_mcp_server.models import HistoryEntry
    from datetime import datetime

    return HistoryEntry(
        instance_id="test-instance-id",
        step_name="test-step",
        outcome_status="success",
        timestamp=datetime.utcnow(),
        user_report={"output": "test-output"},
    )
