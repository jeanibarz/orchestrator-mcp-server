# src/orchestrator_mcp_server/ai_client.py
"""AI Client Module for interacting with Language Models."""

import json
import logging
import os
import re
import time
from typing import Any, NoReturn, cast

import google.generativeai as genai

# Import RequestOptionsType based on Mypy suggestion
from google.generativeai.types import (
    GenerateContentResponse,
    GenerationConfig,
    RequestOptionsType,
)
from google.api_core import exceptions as google_exceptions  # Import google exceptions

from typing_extensions import (
    NotRequired,
    TypedDict,
)

from .models import (
    AbstractAIClient,
    AIInvalidResponseError,
    AIResponse,
    AISafetyError,
    AIServiceAPIError,
    AIServiceError,
    AIServiceTimeoutError,
    HistoryEntry,
    WorkflowInstance,
)

# Import the logger setup
from .logger import setup_logger

# Get the logger for this module
logger = logging.getLogger(__name__)


# Define a structure for optional context arguments
class PromptContext(TypedDict, total=False):
    """Structure for optional context arguments passed to _build_prompt."""

    current_state: NotRequired[WorkflowInstance | None]
    persisted_state: NotRequired[WorkflowInstance | None]
    assumed_step: NotRequired[str | None]
    report: NotRequired[dict[str, Any] | None]
    history: NotRequired[list[HistoryEntry] | None]


def _raise_ai_invalid_response(
    message: str,
    raw_response: str | None = None,
) -> NoReturn:
    """Raise an AIInvalidResponseError."""
    raise AIInvalidResponseError(message, raw_response=raw_response)


class StubbedAIClient(AbstractAIClient):
    """
    A stubbed implementation of the AI Interaction Module for testing purposes.
    (Keeping the Stubbed client for testing)
    """

    # ... (StubbedAIClient implementation remains unchanged) ...

    def determine_first_step(self, _definition_blob: str) -> AIResponse:
        """
        Stubbed method to determine the first step of a workflow.

        Returns a predefined first step.
        """
        # In a real scenario, this would parse the definition_blob and decide.
        # For the stub, we'll return a fixed first step, assuming workflows start with 'Start'.
        return AIResponse(
            next_step_name="Start",
            updated_context={},
            status_suggestion=None,
            reasoning="Stubbed: Returning 'Start' as the first step.",
        )

    def determine_next_step(
        self,
        _definition_blob: str,
        current_state: WorkflowInstance,
        report: dict[str, Any],
        _history: list[HistoryEntry] | None,
    ) -> AIResponse:
        """
        Stubbed method to determine the next step based on current state and report.

        Returns a predefined next step based on simple logic (e.g., report status).
        """
        # Simple stub logic:
        # If report status is 'success', move to a dummy 'NextStep'.
        # If report status is 'failure', move to a dummy 'HandleFailure'.
        # Otherwise, stay on the current step or move to a 'Clarification' step.

        next_step: str = "Start"
        reasoning: str = ""
        status_suggestion: str | None = None
        updated_context: dict[str, Any] = {}

        report_status = report.get("status")

        if report_status == "success":
            next_step = (
                "NextStep"  # Assuming a step named 'NextStep' exists for testing
            )
            reasoning = "Stubbed: Report status was 'success'. Moving to 'NextStep'."
        elif report_status == "failure":
            next_step = "HandleFailure"  # Assuming a step named 'HandleFailure' exists for testing
            reasoning = (
                "Stubbed: Report status was 'failure'. Moving to 'HandleFailure'."
            )
            status_suggestion = "FAILED"  # Suggest failing the workflow on step failure
        elif (
            report_status == "FINISH"
        ):  # Allow client to signal finish via report status
            next_step = "FINISH"
            reasoning = (
                "Stubbed: Report status was 'FINISH'. Signalling workflow completion."
            )
            status_suggestion = "COMPLETED"
        # Example: If current step is 'AskForClarification' and report status is 'data_provided'
        elif (
            current_state.current_step_name == "AskForClarification"
            and report_status == "data_provided"
        ):
            next_step = "ProcessClarification"  # Assuming this step exists
            reasoning = "Stubbed: Received data after clarification request. Moving to 'ProcessClarification'."
        else:
            # Default: Stay on current step or move to a generic next step
            # NOTE: This was the source of the "NextStep" issue when stub was potentially active
            next_step = "NextStep"
            reasoning = (
                f"Stubbed: Report status was '{report_status}'. Moving to 'NextStep'."
            )

        # Example of updating context based on report (stubbed)
        if report_status == "data_provided" and "details" in report:
            updated_context = report[
                "details"
            ]  # Merge details from report into context
            reasoning += " Merging report details into context."

        # Ensure next_step is not None before returning, as AIResponse expects str
        if next_step is None:
            # This case should ideally not happen with the current stub logic,
            # but as a safeguard, default to a known step or raise an error.
            next_step = "Start"  # Default to 'Start' or another safe step

        return AIResponse(
            next_step_name=next_step,  # next_step is guaranteed to be str here
            updated_context=updated_context,
            status_suggestion=status_suggestion,
            reasoning=reasoning,
        )

    def reconcile_and_determine_next_step(
        self,
        _definition_blob: str,
        persisted_state: WorkflowInstance,
        assumed_step: str,
        report: dict[str, Any],
        _history: list[HistoryEntry] | None,
    ) -> AIResponse:
        """
        Stubbed method to reconcile persisted state with assumed state and report.

        Returns a predefined next step based on simple reconciliation logic.
        """
        # Simple stub reconciliation logic:
        # Prioritize persisted state unless the report explicitly indicates completion or failure.
        # If assumed_step is different from persisted_state.current_step_name,
        # log a warning and proceed based on persisted state or report.

        # Determine the initial step name, ensuring it's always str
        _persisted_step_name = persisted_state.current_step_name  # Type: str | None
        initial_step_name: str  # Intermediate variable guaranteed to be str
        reasoning_prefix: str
        if _persisted_step_name is None:
            initial_step_name = "Start"
            reasoning_prefix = (
                "Stubbed: Defaulting to 'Start' (persisted step was None)"
            )
        else:
            # Explicitly cast the assignment within the else block
            initial_step_name = cast("str", _persisted_step_name)
            reasoning_prefix = (
                f"Stubbed: Defaulting to persisted step '{initial_step_name}'"
            )

        # Assign the guaranteed str to next_step
        next_step: str = initial_step_name
        reasoning = f"{reasoning_prefix} for reconciliation."
        # Allow status_suggestion to be None
        status_suggestion: str | None = persisted_state.status
        updated_context = {}  # Start with empty updates

        report_status = report.get("status")

        if assumed_step != persisted_state.current_step_name:
            reasoning += (
                f" (Note: Assumed step '{assumed_step}' differed from persisted step.)"
            )

        # If the report indicates completion or failure, respect that
        if report_status == "FINISH":
            next_step = "FINISH"
            reasoning = (
                "Stubbed: Report status was 'FINISH'. Signalling workflow completion."
            )
            status_suggestion = "COMPLETED"
        elif report_status == "failure":
            next_step = "HandleFailure"  # Assuming a step for failure handling
            reasoning = (
                "Stubbed: Report status was 'failure'. Moving to 'HandleFailure'."
            )
            status_suggestion = "FAILED"
        elif report_status == "success":
            # If resuming after a successful step, move to the *next* step after the persisted one
            # This requires knowing the step order, which the stub doesn't have easily.
            # For simplicity, let's just move to a generic 'NextStep' or rely on the persisted state logic.
            # A more complex stub could use the definition_blob to find the next step.
            # For now, let's use the determine_next_step logic if the report is 'success'
            # as if the user had successfully completed the persisted step.
            # This is a simplification for the stub.
            # Call the determine_next_step logic internally (simplified)
            temp_ai_response = self.determine_next_step(
                _definition_blob,
                persisted_state,
                report,
                _history,
            )
            next_step = temp_ai_response.next_step_name
            reasoning = f"Stubbed: Report status was 'success' during resume. Determined next step based on advance logic: '{next_step}'."
            status_suggestion = temp_ai_response.status_suggestion
            updated_context = (
                temp_ai_response.updated_context
            )  # Include context updates from simulated advance

        # Example of updating context based on report during resume
        if (
            "context_updates" in report
        ):  # Assuming context_updates might be in the report during resume
            updated_context.update(report["context_updates"])
            reasoning += " Merging report context_updates into context."

        return AIResponse(
            next_step_name=next_step,
            updated_context=updated_context,
            status_suggestion=status_suggestion,
            reasoning=reasoning,
        )


class GoogleGenAIClient(AbstractAIClient):
    """Concrete implementation using the Google Generative AI SDK."""

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str = "gemini-1.5-flash-latest",  # Default model
        request_timeout_seconds: int = 60,  # Default timeout
    ) -> None:
        """
        Initialize the GoogleGenAIClient.

        Args:
            api_key: The API key. Reads from GEMINI_API_KEY env var if None.
            model_name: The name of the Gemini model to use.
            request_timeout_seconds: Timeout for API requests in seconds.
        """
        resolved_api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not resolved_api_key:
            msg = "GEMINI_API_KEY not provided or found in environment variables."
            raise ValueError(msg)

        genai.configure(api_key=resolved_api_key)
        self.model = genai.GenerativeModel(model_name)
        self.request_timeout_seconds = request_timeout_seconds
        self.model_name = model_name
        logger.info(f"GoogleGenAIClient initialized with model: {self.model_name}")

    def _build_prompt(
        self,
        task: str,
        definition_blob: str,
        context: PromptContext,
    ) -> str:
        """Construct the prompt for the LLM based on the task and provided context."""
        # (This method is identical to the one from the previous LLMClient)
        current_state = context.get("current_state")
        persisted_state = context.get("persisted_state")
        assumed_step = context.get("assumed_step")
        report = context.get("report")
        history = context.get("history")

        prompt_parts = []

        # System Prompt / Role Definition
        prompt_parts.append(
            'SYSTEM: You are a Workflow Orchestrator Assistant. Your goal is to determine the next logical step in a workflow based on the provided definition, current state, user report, and history. You MUST pay close attention to the \'Orchestrator Guidance\' within each step definition. Your output MUST be a single JSON object matching the provided schema. IMPORTANT: When determining the `next_step_name`, match the intended step from the guidance flexibly, ignoring differences in case or underscores (e.g., "My Step" matches "my_step"). Select the corresponding step name from the schema\'s enum that best matches the intended step. You MUST NOT suggest the status `COMPLETED` or `FAILED` unless there are no valid transitions available according to the Orchestrator Guidance. If the guidance suggests a next step or a conditional transition (e.g., "if something went wrong, transition to step \'X\'"), you MUST suggest the status `RUNNING`.',
        ),  # Updated prompt to mention schema and flexible matching, and clarify status transitions

        # Workflow Definition
        prompt_parts.append(f"WORKFLOW DEFINITION:\n---\n{definition_blob}\n---")

        # Current State & History (for advance/resume)
        if current_state:
            prompt_parts.append(
                f"CURRENT STATE:\n{current_state.model_dump_json(indent=2)}",
            )
        if persisted_state:  # For resume
            prompt_parts.append(
                f"PERSISTED STATE:\n{persisted_state.model_dump_json(indent=2)}",
            )
            prompt_parts.append(f"ASSUMED STEP (from user report): {assumed_step}")

        if history:
            history_list = [entry.model_dump(mode="json") for entry in history]
            prompt_parts.append(
                f"RECENT HISTORY:\n{json.dumps(history_list, indent=2)}",
            )

        # User Input / Report (for advance/resume)
        if report:
            prompt_parts.append(
                f"USER REPORT:\n{json.dumps(report, indent=2)}",
            )

        # Task Instruction
        task_instruction = ""
        if task == "start_workflow":
            # Note: Starting step is now determined by engine, AI not called for this.
            # This method might not be strictly needed for start if engine handles it.
            task_instruction = (
                "Analyze the workflow definition and determine the first step."
            )
        elif task == "advance_workflow":
            task_instruction = f"Based on the current state, the user's report for the last step ('{current_state.current_step_name if current_state else 'N/A'}'), and the workflow definition (especially Orchestrator Guidance), determine the next logical step."
        elif task == "resume_workflow":
            task_instruction = f"The user is resuming workflow instance '{persisted_state.instance_id if persisted_state else 'N/A'}'. Their report indicates their current situation, and they believe they were on step '{assumed_step}'. The persisted server state shows the last known step was '{persisted_state.current_step_name if persisted_state else 'N/A'}'. Reconcile the user's report and assumed state with the persisted state and history, using the workflow definition (especially Orchestrator Guidance), to determine the correct next logical step."
        else:
            msg = f"Unknown AI task: {task}"
            raise ValueError(msg)

        # Add instruction about the updated_context format
        task_instruction += " Format any context updates in the 'updated_context' field as an array of objects, where each object has a 'key' and a 'value' string property."

        prompt_parts.append(
            f"TASK: {task_instruction} Output ONLY the JSON object matching the provided schema.",
        )

        return "\n\n".join(prompt_parts)

    def _call_gemini_api(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Call the Google GenAI API with structured output constraints and error handling."""
        max_retries = 1
        retry_delay_seconds = 5

        generation_config = GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
            # Add other config like temperature if needed
        )

        # Use RequestOptionsType for correct typing and cast the literal
        request_options: RequestOptionsType = cast(
            RequestOptionsType, {"timeout": self.request_timeout_seconds}
        )

        for attempt in range(max_retries + 1):
            try:
                logger.debug(
                    f"Calling Gemini API (Attempt {attempt + 1}/{max_retries + 1}). Schema: {json.dumps(schema)}"
                )

                # Log the prompt before sending
                logger.info(f"AI Call Prompt:\n{prompt}")

                response: GenerateContentResponse = self.model.generate_content(
                    contents=prompt,
                    generation_config=generation_config,
                    request_options=request_options,
                )

                # Log raw response text
                raw_response_text = response.text
                logger.info(f"AI Response Raw Text:\n{raw_response_text}")

                # Basic validation: Check if response text exists
                if not raw_response_text:
                    # Check for safety ratings or prompt feedback if response is empty
                    try:
                        if response.prompt_feedback.block_reason:
                            reason = response.prompt_feedback.block_reason.name
                            msg = f"Gemini API call blocked due to safety settings: {reason}"
                            logger.error(msg)
                            raise AISafetyError(msg)
                    except (
                        ValueError,
                        IndexError,
                    ):  # Handle cases where feedback/parts might be missing
                        pass  # No block reason found, might be other issue

                    _raise_ai_invalid_response(
                        "Gemini API returned an empty response.",
                        raw_response=raw_response_text,
                    )

                # Parse the JSON response text
                try:
                    response_json = json.loads(raw_response_text)
                    # Log the parsed JSON response
                    logger.info(
                        f"AI Response Parsed JSON:\n{json.dumps(response_json, indent=2)}"
                    )

                    if (
                        not isinstance(response_json, dict)
                        or "next_step_name" not in response_json
                    ):
                        _raise_ai_invalid_response(
                            "Gemini response is not a valid JSON object or missing 'next_step_name'.",
                            raw_response=raw_response_text,
                        )
                    # Schema adherence is expected due to generation_config,
                    # but basic structure check is still useful.
                    return response_json
                except json.JSONDecodeError:
                    _raise_ai_invalid_response(
                        "Gemini response is not valid JSON.",
                        raw_response=raw_response_text,
                    )

            except google_exceptions.RetryError as e:
                logger.warning(f"Gemini API RetryError (Attempt {attempt + 1}): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay_seconds)
                    continue
                else:
                    msg = f"Gemini API call failed after {max_retries + 1} attempts due to retryable errors."
                    raise AIServiceTimeoutError(
                        msg
                    ) from e  # Treat persistent retry errors as timeout
            except google_exceptions.GoogleAPIError as e:
                logger.error(f"Gemini API GoogleAPIError (Attempt {attempt + 1}): {e}")
                # Treat as non-retryable API error
                msg = f"Gemini API returned an error: {e}"
                # Attempt to get status code if available
                status_code = getattr(e, "code", None)
                raise AIServiceAPIError(
                    msg, status_code=status_code, response_body=str(e)
                ) from e
            except AISafetyError:  # Re-raise safety errors immediately
                raise
            except (
                AIInvalidResponseError
            ):  # Re-raise invalid response errors immediately
                raise
            except Exception as e:  # Catch other unexpected errors
                logger.error(
                    f"Unexpected error calling Gemini API (Attempt {attempt + 1}): {e}",
                    exc_info=True,
                )
                if attempt < max_retries:
                    time.sleep(retry_delay_seconds)
                    continue
                else:
                    msg = f"An unexpected error occurred during Gemini API call after {max_retries + 1} attempts: {e}"
                    raise AIServiceError(msg) from e

        # Should not be reachable if max_retries >= 0
        msg = "Gemini API call failed unexpectedly after all retries."
        raise AIServiceError(msg)

    def _process_llm_response(self, llm_response_json: dict[str, Any]) -> AIResponse:
        """Processes the raw LLM JSON response, converting context updates."""
        raw_updates = llm_response_json.get(
            "updated_context"
        )  # This will be a list or None
        processed_updates: dict[str, Any] = {}
        if isinstance(raw_updates, list):
            for item in raw_updates:
                if isinstance(item, dict) and "key" in item and "value" in item:
                    # Basic type check/conversion could happen here if value wasn't just STRING
                    processed_updates[item["key"]] = item["value"]
                else:
                    logger.warning(
                        f"Skipping malformed context update item from LLM: {item}"
                    )

        # Ensure next_step_name exists (already checked in _call_gemini_api, but good practice)
        next_step_name = llm_response_json.get("next_step_name")
        if not isinstance(next_step_name, str):
            # This case should ideally be caught earlier by schema validation or _call_gemini_api checks
            _raise_ai_invalid_response(
                f"LLM response missing or invalid 'next_step_name': {llm_response_json}",
                raw_response=json.dumps(llm_response_json),  # Log the problematic JSON
            )

        return AIResponse(
            next_step_name=next_step_name,  # Use validated/extracted name
            updated_context=processed_updates,  # Use the processed dictionary
            status_suggestion=llm_response_json.get("status_suggestion"),  # Optional
            reasoning=llm_response_json.get("reasoning"),  # Optional
        )

    def _generate_response_schema(self, definition_blob: str) -> dict[str, Any]:
        """Generates the JSON schema for the AI response dynamically."""
        valid_step_names = ["FINISH", "FAILED"]
        # Updated regex to match ordered (1.) or unordered (-, *, +) lists with links
        step_link_pattern = re.compile(
            r"^[ \t]*(\d+\.|[-*+]) [ \t]*\[([^\]]+)\]\(([^)]+\.md)\)",
            re.MULTILINE,
        )
        for line in definition_blob.splitlines():
            match = step_link_pattern.match(line)
            if match:
                # Group 2 is the step name in the updated regex
                step_name = match.group(2).strip()
                if step_name:  # Ensure step name is not empty
                    valid_step_names.append(step_name)

        # Build the response schema dynamically using OpenAPI format
        response_schema = {
            "type": "OBJECT",
            "properties": {
                "next_step_name": {"type": "STRING", "enum": valid_step_names},
                "updated_context": {
                    "type": "ARRAY",
                    "description": "List of key-value pairs to update the workflow context. Each item should have a 'key' and a 'value'.",
                    "nullable": True,
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "key": {
                                "type": "STRING",
                                "description": "The context key to update.",
                            },
                            "value": {
                                "type": "STRING",
                                "description": "The context value (as a string).",
                            },
                        },
                        "required": ["key", "value"],
                    },
                },
                "status_suggestion": {
                    "type": "STRING",
                    "enum": ["RUNNING", "SUSPENDED", "COMPLETED", "FAILED"],
                    "nullable": True,
                    "description": "Suggested new status for the workflow instance (optional).",
                },
                "reasoning": {
                    "type": "STRING",
                    "nullable": True,
                    "description": "Explanation for the chosen next step (optional).",
                },
            },
            "required": ["next_step_name"],
        }
        # Log the generated list of valid step names for debugging
        logger.info(f"Generated valid step names for schema: {valid_step_names}")
        return response_schema

    def determine_first_step(self, definition_blob: str) -> AIResponse:
        """
        Determines the first step.
        NOTE: In the current engine design, the engine determines the first step directly.
              This method might not be called if using the standard engine flow.
              If needed, it would call the AI, but likely without schema constraints
              as the first step isn't chosen from a list in the same way.
        """
        # For now, raise NotImplementedError as the engine handles first step determination.
        # If AI were needed for the *very* first step selection based on definition analysis,
        # this would need a different prompt and potentially no schema constraint.
        raise NotImplementedError("Engine determines the first step directly.")

    def determine_next_step(
        self,
        definition_blob: str,
        current_state: WorkflowInstance,
        report: dict[str, Any],
        history: list[HistoryEntry] | None,
    ) -> AIResponse:
        """Determine the next step based on current state and user report using Google GenAI."""
        prompt = self._build_prompt(
            task="advance_workflow",
            definition_blob=definition_blob,
            context={
                "current_state": current_state,
                "report": report,
                "history": history,
            },
        )
        schema = self._generate_response_schema(definition_blob)
        llm_response_json = self._call_gemini_api(prompt, schema=schema)
        # Process the response to handle the updated_context format
        return self._process_llm_response(llm_response_json)

    def reconcile_and_determine_next_step(
        self,
        definition_blob: str,
        persisted_state: WorkflowInstance,
        assumed_step: str,
        report: dict[str, Any],
        history: list[HistoryEntry] | None,
    ) -> AIResponse:
        """Reconcile state and determine the next step during workflow resumption using Google GenAI."""
        prompt = self._build_prompt(
            task="resume_workflow",
            definition_blob=definition_blob,
            context={
                "persisted_state": persisted_state,
                "assumed_step": assumed_step,
                "report": report,
                "history": history,
            },
        )
        schema = self._generate_response_schema(definition_blob)
        llm_response_json = self._call_gemini_api(prompt, schema=schema)
        # Process the response to handle the updated_context format
        return self._process_llm_response(llm_response_json)
