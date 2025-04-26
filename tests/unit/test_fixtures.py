"""
Tests for the pytest fixtures defined in conftest.py.
"""

import pytest
from datetime import datetime

from orchestrator_mcp_server.models import WorkflowInstance, HistoryEntry


def test_mock_workflow_instance_fixture(mock_workflow_instance):
    """Test that the mock_workflow_instance fixture returns a valid WorkflowInstance."""
    assert isinstance(mock_workflow_instance, WorkflowInstance)
    assert mock_workflow_instance.instance_id == "test-instance-id"
    assert mock_workflow_instance.workflow_name == "test-workflow"
    assert mock_workflow_instance.current_step_name == "test-step"
    assert mock_workflow_instance.status == "RUNNING"
    assert isinstance(mock_workflow_instance.context, dict)
    assert isinstance(mock_workflow_instance.created_at, datetime)
    assert isinstance(mock_workflow_instance.updated_at, datetime)
    assert mock_workflow_instance.completed_at is None


def test_mock_report_fixture(mock_report):
    """Test that the mock_report fixture returns a valid report dictionary."""
    assert isinstance(mock_report, dict)
    assert mock_report["step_id"] == "test-step"
    assert mock_report["result"] == {"output": "test-output"}
    assert mock_report["status"] == "success"


def test_mock_history_entry_fixture(mock_history_entry):
    """Test that the mock_history_entry fixture returns a valid HistoryEntry."""
    assert isinstance(mock_history_entry, HistoryEntry)
    assert mock_history_entry.instance_id == "test-instance-id"
    assert mock_history_entry.step_name == "test-step"
    assert mock_history_entry.outcome_status == "success"
    assert isinstance(mock_history_entry.timestamp, datetime)
    assert mock_history_entry.user_report == {"output": "test-output"}


def test_google_generativeai_mock():
    """Test that google.generativeai is properly mocked."""
    import google.generativeai
    from unittest.mock import MagicMock

    assert isinstance(google.generativeai, MagicMock)


def test_generate_content_response_mock():
    """Test that GenerateContentResponse is properly mocked."""
    from google.generativeai.types import GenerateContentResponse

    response = GenerateContentResponse(text="test response")
    assert response.text == "test response"
    assert response.prompt_feedback.block_reason is None
