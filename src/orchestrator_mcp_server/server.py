"""Main MCP server module for the Workflow Orchestrator using FastMCP."""

import asyncio
import json
import os
import sys
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, cast  # Added cast

from fastmcp import Context, FastMCP  # Updated import source
from pydantic import ValidationError

# Updated AI Client import (Removed LLMClient)
from .ai_client import (
    AbstractAIClient,
    AIServiceError,
    GoogleGenAIClient,
    StubbedAIClient,
)
from .database import initialize_database
from .definition_service import (
    DefinitionNotFoundError,
    DefinitionParsingError,
    WorkflowDefinitionService,
)
from .engine import OrchestrationEngine, OrchestrationEngineError
from .models import (
    AdvanceResumeWorkflowOutput,
    AdvanceWorkflowInput,
    GetWorkflowStatusInput,
    GetWorkflowStatusOutput,
    InstanceNotFoundError,
    ListWorkflowsOutput,
    PersistenceError,
    ResumeWorkflowInput,
    StartWorkflowInput,
    StartWorkflowOutput,
    WorkflowInfo,
)
from .persistence import WorkflowPersistenceRepository

# --- Configuration ---
WORKFLOW_DEFINITIONS_DIR = os.environ.get("WORKFLOW_DEFINITIONS_DIR", "./workflows")
WORKFLOW_DB_PATH = os.environ.get("WORKFLOW_DB_PATH", "./data/workflows.sqlite")
# Default to NOT using stub client unless explicitly set
USE_STUB_AI_CLIENT = os.environ.get("USE_STUB_AI_CLIENT", "false").lower() == "true"

# --- Gemini Configuration (Mandatory Model Name) ---
GEMINI_MODEL_NAME = os.environ.get("GEMINI_MODEL_NAME")
if not USE_STUB_AI_CLIENT and not GEMINI_MODEL_NAME:
    # Raise error only if we intend to use the real client
    raise ValueError("Mandatory environment variable GEMINI_MODEL_NAME is not set.")

GEMINI_REQUEST_TIMEOUT_SECONDS = int(
    os.environ.get("GEMINI_REQUEST_TIMEOUT_SECONDS", "60")
)
# GEMINI_API_KEY is read directly by the client from env var

# --- Lifespan Management ---


# Define a context structure to hold initialized components
class ServerContext:
    def __init__(self) -> None:
        self.persistence_repo: WorkflowPersistenceRepository | None = None
        self.definition_service: WorkflowDefinitionService | None = None
        self.ai_client: AbstractAIClient | None = None
        self.orchestration_engine: OrchestrationEngine | None = None


@asynccontextmanager
async def server_lifespan(
    server: FastMCP,
) -> AsyncIterator[ServerContext]:  # Changed server type hint
    """Manage application lifecycle and initialize components."""
    app_context = ServerContext()
    try:
        # Initialize the database
        initialize_database()  # Assuming this sets up the DB file if needed

        # Initialize Persistence Repository
        app_context.persistence_repo = WorkflowPersistenceRepository()

        # Initialize Workflow Definition Service
        app_context.definition_service = WorkflowDefinitionService(
            WORKFLOW_DEFINITIONS_DIR
        )

        # Initialize AI Client
        if USE_STUB_AI_CLIENT:
            app_context.ai_client = StubbedAIClient()
            print("Using StubbedAIClient.")
        else:
            # GEMINI_MODEL_NAME is guaranteed to be non-empty here if USE_STUB_AI_CLIENT is false
            print(f"Using GoogleGenAIClient with model: {GEMINI_MODEL_NAME}")
            try:  # Correctly indented under else
                app_context.ai_client = GoogleGenAIClient(
                    # Cast is safe due to the check above
                    model_name=cast("str", GEMINI_MODEL_NAME),
                    request_timeout_seconds=GEMINI_REQUEST_TIMEOUT_SECONDS,
                    # api_key is handled internally via os.environ.get("GEMINI_API_KEY")
                )
            except ValueError as e:  # Correctly indented under else
                # Catch error if API key is missing or other init issues
                print(
                    f"FATAL: Failed to initialize GoogleGenAIClient: {e}",
                    file=sys.stderr,
                )
                raise RuntimeError(f"AI Client initialization failed: {e}") from e

        # Ensure AI client was initialized before creating engine (Correctly indented under try/except of lifespan)
        if app_context.ai_client is None:
            # This should theoretically not happen due to checks above, but satisfies mypy
            raise RuntimeError(
                "AI Client failed to initialize but no exception was caught."
            )

        # Initialize Orchestration Engine (Correctly indented under try/except of lifespan)
        app_context.orchestration_engine = OrchestrationEngine(
            definition_service=app_context.definition_service,
            persistence_repo=app_context.persistence_repo,
            ai_client=app_context.ai_client,  # Correctly indented parameter
        )
        print("Orchestrator MCP Server components initialized successfully.")
        yield app_context
    except Exception as e:
        print(f"FATAL: Failed to initialize server components: {e}", file=sys.stderr)
        # Optionally re-raise or handle specific exceptions differently
        raise RuntimeError(f"Server initialization failed: {e}") from e
    finally:
        # Add cleanup logic here if needed (e.g., closing DB connections)
        print("Orchestrator MCP Server shutting down.")


# --- MCP Server Initialization ---
mcp = FastMCP(
    "orchestrator-mcp-server",
    version="0.1.0",
    lifespan=server_lifespan,
)


# --- Helper to get engine from context ---
def _get_engine(ctx: Context) -> OrchestrationEngine:
    """Safely retrieve the orchestration engine from the lifespan context."""
    if not ctx.request_context or not hasattr(ctx.request_context, "lifespan_context"):
        raise RuntimeError("Server context not available.")
    server_context = cast(ServerContext, ctx.request_context.lifespan_context)
    if not server_context.orchestration_engine:
        raise RuntimeError("Orchestration engine not initialized.")
    return server_context.orchestration_engine


def _get_persistence_repo(ctx: Context) -> WorkflowPersistenceRepository:
    """Safely retrieve the persistence repository from the lifespan context."""
    if not ctx.request_context or not hasattr(ctx.request_context, "lifespan_context"):
        raise RuntimeError("Server context not available.")
    server_context = cast(ServerContext, ctx.request_context.lifespan_context)
    if not server_context.persistence_repo:
        raise RuntimeError("Persistence repository not initialized.")
    return server_context.persistence_repo


# --- Tool Implementations ---


@mcp.tool()
def list_workflows(ctx: Context) -> str:
    """List available workflow definitions."""
    try:
        engine = _get_engine(ctx)
        workflows_list = engine.list_workflows()
        output = ListWorkflowsOutput(
            workflows=[
                WorkflowInfo(
                    id=wf, name=wf, description="", steps={}
                )  # Simplified for now
                for wf in workflows_list
            ]
        )
        return output.model_dump_json(indent=2)
    except Exception as e:
        # Log the error
        print(f"Error in list_workflows: {e}", file=sys.stderr)
        # Return a user-friendly error message
        return json.dumps({"error": f"Failed to list workflows: {e}"})


@mcp.tool()
def start_workflow(input_data: StartWorkflowInput, ctx: Context) -> str:
    """Starts a workflow by its definition name."""
    try:
        engine = _get_engine(ctx)
        result = engine.start_workflow(
            workflow_name=input_data.workflow_name,
            initial_context=input_data.context,
        )
        output = StartWorkflowOutput.model_validate(result.model_dump())
        return output.model_dump_json(indent=2)
    except (
        ValidationError,
        ValueError,
        DefinitionNotFoundError,
        PersistenceError,
        AIServiceError,
        OrchestrationEngineError,
    ) as e:
        print(f"Error in start_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {"error": f"Failed to start workflow '{input_data.workflow_name}': {e}"}
        )
    except Exception as e:
        print(f"Unexpected error in start_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"An unexpected error occurred while starting workflow '{input_data.workflow_name}'."
            }
        )


@mcp.tool()
def get_workflow_status(input_data: GetWorkflowStatusInput, ctx: Context) -> str:
    """Gets the current status of a running workflow instance."""
    try:
        repo = _get_persistence_repo(ctx)
        instance_state = repo.get_instance(input_data.instance_id)
        output = GetWorkflowStatusOutput.model_validate(instance_state.model_dump())
        return output.model_dump_json(indent=2)
    except InstanceNotFoundError:
        return json.dumps(
            {"error": f"Workflow instance '{input_data.instance_id}' not found."}
        )
    except (PersistenceError, ValidationError) as e:
        print(f"Error in get_workflow_status: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"Failed to get status for instance '{input_data.instance_id}': {e}"
            }
        )
    except Exception as e:
        print(f"Unexpected error in get_workflow_status: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"An unexpected error occurred while getting status for instance '{input_data.instance_id}'."
            }
        )


@mcp.tool()
def advance_workflow(input_data: AdvanceWorkflowInput, ctx: Context) -> str:
    """Reports the outcome of the previously issued step and requests the next step."""
    try:
        engine = _get_engine(ctx)
        result = engine.advance_workflow(
            instance_id=input_data.instance_id,
            report=input_data.report,
            context_updates=input_data.context_updates,
        )
        output = AdvanceResumeWorkflowOutput.model_validate(result.model_dump())
        return output.model_dump_json(indent=2)
    except (
        ValidationError,
        ValueError,
        InstanceNotFoundError,
        PersistenceError,
        AIServiceError,
        OrchestrationEngineError,
    ) as e:
        print(f"Error in advance_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"Failed to advance workflow instance '{input_data.instance_id}': {e}"
            }
        )
    except Exception as e:
        print(f"Unexpected error in advance_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"An unexpected error occurred while advancing workflow instance '{input_data.instance_id}'."
            }
        )


@mcp.tool()
def resume_workflow(input_data: ResumeWorkflowInput, ctx: Context) -> str:
    """Reconnects to an existing workflow instance."""
    try:
        engine = _get_engine(ctx)
        result = engine.resume_workflow(
            instance_id=input_data.instance_id,
            assumed_step=input_data.assumed_current_step_name,
            report=input_data.report,
            context_updates=input_data.context_updates,
        )
        output = AdvanceResumeWorkflowOutput.model_validate(result.model_dump())
        return output.model_dump_json(indent=2)
    except (
        ValidationError,
        ValueError,
        InstanceNotFoundError,
        PersistenceError,
        AIServiceError,
        OrchestrationEngineError,
    ) as e:
        print(f"Error in resume_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"Failed to resume workflow instance '{input_data.instance_id}': {e}"
            }
        )
    except Exception as e:
        print(f"Unexpected error in resume_workflow: {e}", file=sys.stderr)
        return json.dumps(
            {
                "error": f"An unexpected error occurred while resuming workflow instance '{input_data.instance_id}'."
            }
        )


# --- Main Execution ---
async def main() -> None:
    """Run the FastMCP server using the appropriate async method."""
    # Call the async stdio runner since __main__.py already uses asyncio.run()
    await mcp.run_stdio_async()


# Note: The __main__ block in __main__.py will call this main function
