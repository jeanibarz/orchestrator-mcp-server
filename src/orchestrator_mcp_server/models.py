"""Defines Pydantic models for workflow state, history, exceptions, and MCP tool I/O."""

import json  # Import json for serialization/deserialization
import uuid
from abc import ABC, abstractmethod  # Import ABC and abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# --- Custom Exceptions ---


# Define custom exceptions for persistence errors as per Section 6.4
class PersistenceError(Exception):
    """Base exception for persistence-related errors."""


class InstanceNotFoundError(PersistenceError):
    """Exception raised when a workflow instance is not found."""


class PersistenceConnectionError(PersistenceError):
    """Exception raised for database connection errors."""


class PersistenceQueryError(PersistenceError):
    """Exception raised for database query execution errors."""

    def __init__(
        self,
        message: str,
        original_error: Exception,
    ) -> None:  # Changed type hint to Exception
        """
        Initialize PersistenceQueryError.

        Args:
            message: The error message.
            original_error: The underlying database exception.

        """
        super().__init__(message)
        self.original_error = original_error


# Define custom exceptions for AI interaction errors as per Section 6.5
class AIServiceError(Exception):
    """Base exception for AI service interaction errors."""


class AIServiceTimeoutError(AIServiceError):
    """Exception raised when the AI service request times out."""


class AIInvalidResponseError(AIServiceError):
    """Exception raised when the AI service returns an invalid or unparseable response."""

    def __init__(self, message: str, raw_response: str | None = None) -> None:
        """
        Initialize AIInvalidResponseError.

        Args:
            message: The error message.
            raw_response: The raw, unparseable response text from the AI service.

        """
        super().__init__(message)
        self.raw_response = raw_response


class AIServiceAPIError(AIServiceError):
    """Exception raised for errors returned by the AI service API (e.g., 4xx, 5xx)."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str | None = None,
    ) -> None:
        """
        Initialize AIServiceAPIError.

        Args:
            message: The error message.
            status_code: The HTTP status code returned by the AI service.
            response_body: The body of the error response from the AI service.

        """
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class AISafetyError(AIServiceError):
    """Exception raised when the AI service flags content as unsafe."""


# Define custom exceptions for definition service errors as per Section 6.6
class DefinitionServiceError(Exception):
    """Base exception for workflow definition service errors."""


class DefinitionNotFoundError(DefinitionServiceError):
    """Exception raised when a workflow definition or file is not found."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
    ) -> None:  # Added file_path parameter
        """
        Initialize DefinitionNotFoundError.

        Args:
            message: The error message.
            file_path: The path to the file that was not found.

        """
        super().__init__(message)
        self.file_path = file_path


class DefinitionParsingError(DefinitionServiceError):
    """Exception raised when a workflow definition file has a parsing error."""

    def __init__(
        self,
        message: str,
        file_path: str | None = None,
    ) -> None:  # Added file_path parameter
        """
        Initialize DefinitionParsingError.

        Args:
            message: The error message.
            file_path: The path to the file where the parsing error occurred.

        """
        super().__init__(message)
        self.file_path = file_path


# Define engine-specific errors if needed, or reuse existing ones
class OrchestrationEngineError(Exception):
    """Base exception for Orchestration Engine errors."""


class WorkflowAlreadyCompletedError(OrchestrationEngineError):
    """Exception raised when attempting to advance/resume a completed workflow."""


# --- Abstract AI Client Interface ---
class AbstractAIClient(ABC):
    """
    Abstract base class for AI Interaction Module implementations.

    Defines the interface for interacting with an LLM to orchestrate workflows.
    """

    @abstractmethod
    def determine_first_step(
        self,
        definition_blob: str,
    ) -> "AIResponse":  # Use forward reference for AIResponse
        """Determine the very first step for a new workflow instance."""

    @abstractmethod
    def determine_next_step(
        self,
        definition_blob: str,
        current_state: "WorkflowInstance",
        report: dict[str, Any],
        history: list["HistoryEntry"] | None,
    ) -> "AIResponse":  # Use forward references
        """Determine the next step based on current state and user report."""

    @abstractmethod
    def reconcile_and_determine_next_step(
        self,
        definition_blob: str,
        persisted_state: "WorkflowInstance",
        assumed_step: str,
        report: dict[str, Any],
        history: list["HistoryEntry"] | None,
    ) -> "AIResponse":  # Use forward references
        """Reconcile state and determine the next step during workflow resumption."""


# --- Core Orchestrator Data Structures ---


class WorkflowInfo(BaseModel):
    """Information about a workflow definition."""

    id: str = Field(..., description="The unique ID of the workflow definition.")
    name: str = Field(
        ...,
        description="The human-readable name of the workflow definition.",
    )
    description: str = Field(
        ...,
        description="A brief description of the workflow definition.",
    )
    # Add fields to represent the steps and rules from the definition
    steps: dict[str, dict[str, Any]] = Field(
        ...,
        description="A map of step IDs to step details (instructions, next steps, etc.).",
    )


class WorkflowInstance(BaseModel):
    """The current state of a workflow instance, mapping to the workflow_instances table."""

    instance_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="The unique ID of the workflow instance.",
    )
    workflow_name: str = Field(
        ...,
        description="The name of the workflow definition this instance is based on.",
    )
    current_step_name: str | None = Field(  # Allow None
        ...,
        description="The name of the last step determined by the orchestrator (can be None initially).",
    )
    status: str = Field(
        ...,
        description="Current status ('RUNNING', 'SUSPENDED', 'COMPLETED', 'FAILED').",
    )
    context: dict[str, Any] = Field(
        {},
        description="Workflow context stored as JSON text in DB.",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Instance creation time.",
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last modification time.",
    )
    completed_at: datetime | None = Field(
        None,
        description="Instance completion/failure time (nullable).",
    )

    def to_db_row(self) -> dict[str, Any]:
        """Convert the model to a dictionary suitable for database insertion/update."""
        return {
            "instance_id": self.instance_id,
            "workflow_name": self.workflow_name,
            "current_step_name": self.current_step_name,
            "status": self.status,
            "context": json.dumps(self.context),  # Serialize context to JSON string
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "WorkflowInstance":
        """Create a WorkflowInstance model from a database row."""
        return cls(
            instance_id=row["instance_id"],
            workflow_name=row["workflow_name"],
            current_step_name=row["current_step_name"],
            status=row["status"],
            context=(
                json.loads(row["context"]) if row["context"] else {}
            ),  # Deserialize context from JSON string
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            completed_at=(
                datetime.fromisoformat(row["completed_at"])
                if row["completed_at"]
                else None
            ),
        )


class HistoryEntry(BaseModel):
    """Represents an entry in the workflow_history table."""

    history_entry_id: int | None = Field(
        None,
        description="Auto-incrementing ID for the history entry (set by DB).",
    )
    instance_id: str = Field(..., description="Links to workflow_instances table.")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Time of this history event.",
    )
    step_name: str = Field(
        ...,
        description="The step being reported on / just finished OR 'RESUME_ATTEMPT'.",
    )
    user_report: dict[str, Any] | None = Field(
        None,
        description="User's report for this step/resume (as JSON text in DB).",
    )
    outcome_status: str | None = Field(
        None,
        description="Status derived from report ('success', 'failure', etc.) OR 'RESUMING'.",
    )
    determined_next_step: str | None = Field(
        None,
        description="The next step decided by the orchestrator after this event.",
    )

    def to_db_row(self) -> dict[str, Any]:
        """Convert the model to a dictionary suitable for database insertion."""
        return {
            "instance_id": self.instance_id,
            "timestamp": self.timestamp.isoformat(),
            "step_name": self.step_name,
            "user_report": (
                json.dumps(self.user_report) if self.user_report is not None else None
            ),  # Serialize report to JSON string
            "outcome_status": self.outcome_status,
            "determined_next_step": self.determined_next_step,
        }

    @classmethod
    def from_db_row(cls, row: dict[str, Any]) -> "HistoryEntry":
        """Create a HistoryEntry model from a database row."""
        return cls(
            history_entry_id=row["history_entry_id"],
            instance_id=row["instance_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            step_name=row["step_name"],
            user_report=(
                json.loads(row["user_report"]) if row["user_report"] else None
            ),  # Deserialize report from JSON string
            outcome_status=row["outcome_status"],
            determined_next_step=row["determined_next_step"],
        )


# The existing ReportPayload model seems to be for API input, not directly for DB storage.
# Keeping it for now, but the HistoryEntry model is the one mapping to the DB table.
class ReportPayload(BaseModel):
    """Payload sent by the Executor to report a step result."""

    step_id: str = Field(
        ...,
        description="The ID of the step the Executor just attempted/completed.",
    )
    result: Any = Field(
        ...,
        description="Data payload containing the outcome or information gathered during the step. Structure depends on the step.",
    )
    status: str = Field(
        ...,
        description="How the step execution went from the Executor's perspective ('success', 'failure', 'data_provided', 'needs_clarification').",
    )
    details: dict[str, Any] | None = Field(
        None,
        description="Optional: object containing structured output or user feedback (from TS).",
    )
    message: str | None = Field(
        None,
        description="Optional: Free-text description of actions, struggles, outcome (from TS).",
    )
    error: str | None = Field(
        None,
        description="Optional: Error message if status is 'failure' (from TS).",
    )


# --- MCP Tool Input/Output Models (based on TS api.types.ts) ---
# These models are for API request/response validation and can remain largely as is,
# referencing the new WorkflowInstance and HistoryEntry models where appropriate.

# --- MCP Tool Input/Output Models (based on TS api.types.ts) ---
# These models are for API request/response validation and can remain largely as is,
# referencing the new WorkflowInstance and HistoryEntry models where appropriate.


# Input for 'start_workflow' tool
class StartWorkflowInput(BaseModel):
    """Input model for the 'start_workflow' MCP tool."""

    workflow_name: str = Field(
        ...,
        description="The name of the workflow definition to start (required).",
    )  # Changed from workflow_id
    context: dict[str, Any] = Field(
        {},
        description="An initial key-value map (JSON object) to populate the workflow instance's context (optional).",
    )


# Output for 'start_workflow' tool
class StartWorkflowOutput(BaseModel):  # Changed to explicitly define output structure
    """Output model for the 'start_workflow' MCP tool."""

    instance_id: str = Field(
        ...,
        description="The unique ID generated for this new workflow instance.",
    )
    next_step: dict[str, str] = Field(
        ...,
        description="An object containing details for the first step determined by the AI.",
    )
    current_context: dict[str, Any] = Field(
        ...,
        description="The context object for the instance after initialization.",
    )


# Input for 'advance_workflow' tool
class AdvanceWorkflowInput(BaseModel):
    """Input model for the 'advance_workflow' MCP tool."""

    instance_id: str = Field(
        ...,
        description="The unique ID of the workflow instance to advance (required).",
    )
    report: ReportPayload = Field(
        ...,
        description="An object detailing the outcome of the previous step (required).",
    )
    context_updates: dict[str, Any] = Field(
        {},
        description="Optional: A key-value map of changes to be merged into the workflow instance's context.",
    )


# Output for 'advance_workflow' and 'resume_workflow' tools
class AdvanceResumeWorkflowOutput(
    BaseModel,
):  # Changed to explicitly define output structure
    """Output model for the 'advance_workflow' and 'resume_workflow' MCP tools."""

    instance_id: str = Field(
        ...,
        description="The ID of the workflow instance being advanced/resumed.",
    )
    next_step: dict[str, str] = Field(
        ...,
        description="An object containing details for the next step determined by the AI.",
    )
    current_context: dict[str, Any] = Field(
        ...,
        description="The context object for the instance after processing.",
    )


# Input for 'resume_workflow' tool
class ResumeWorkflowInput(BaseModel):
    """Input model for the 'resume_workflow' MCP tool."""

    instance_id: str = Field(
        ...,
        description="The unique ID of the workflow instance to resume (required).",
    )
    assumed_current_step_name: str = Field(
        ...,
        description="The name of the step the client believes it is currently on or has just completed (required).",
    )
    report: ReportPayload = Field(
        ...,
        description="An object detailing the client's current situation (required).",
    )
    context_updates: dict[str, Any] = Field(
        {},
        description="Optional: A key-value map of changes to be merged into the workflow instance's context.",
    )


# Input for 'get_workflow_status' tool
class GetWorkflowStatusInput(BaseModel):
    """Input model for the 'get_workflow_status' MCP tool."""

    instance_id: str = Field(
        ...,
        description="The ID of the workflow instance to get the status for (required).",
    )


# Output for 'get_workflow_status' tool
class GetWorkflowStatusOutput(
    WorkflowInstance,
):  # Output is the full WorkflowInstance state
    """Output is the current WorkflowInstance state."""


# Output for 'list_workflows' tool
class ListWorkflowsOutput(BaseModel):
    """Output model for the 'list_workflows' MCP tool."""

    workflows: list[WorkflowInfo] = Field(
        ...,
        description="An array of available workflow definitions.",
    )


# --- AI Interaction Data Structures ---


class AIResponse(BaseModel):
    """Expected JSON response format from the AI service."""

    next_step_name: str = Field(
        ...,
        description="The name of the next step the orchestrator should transition to.",
    )
    updated_context: dict[str, Any] = Field(
        {},
        description="An object containing key-value pairs to be merged into the existing workflow instance context.",
    )
    status_suggestion: str | None = Field(
        None,
        description="The AI can suggest a change to the overall workflow instance status.",
    )
    reasoning: str | None = Field(
        None,
        description="A brief explanation from the LLM on why it chose the next_step_name.",
    )
