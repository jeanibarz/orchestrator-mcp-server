"""Core Orchestration Engine for managing workflow execution."""

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

# Import components and models
from .ai_client import AIServiceError
from .definition_service import (
    DefinitionNotFoundError,
    DefinitionParsingError,
    DefinitionServiceError,
    WorkflowDefinitionService,
)
from .models import (
    AbstractAIClient,  # Import AbstractAIClient from models
    AdvanceResumeWorkflowOutput,
    AIResponse,
    HistoryEntry,
    ReportPayload,
    StartWorkflowOutput,
    WorkflowInstance,
)
from .persistence import (
    InstanceNotFoundError,
    PersistenceError,
    WorkflowPersistenceRepository,
)

# Import the logger setup
from .logger import setup_logger

# Configure logging
logger = logging.getLogger(__name__)

# Setup the logger (will only configure handlers once)
setup_logger()


# Define engine-specific errors if needed, or reuse existing ones
class OrchestrationEngineError(Exception):
    """Base exception for Orchestration Engine errors."""


class WorkflowAlreadyCompletedError(OrchestrationEngineError):
    """Exception raised when attempting to advance/resume a completed workflow."""


class OrchestrationEngine:
    """
    The core Orchestration Engine responsible for coordinating workflow execution.

    Manages interactions between Definition Service, Persistence, and AI Client.
    """

    def __init__(
        self,
        definition_service: WorkflowDefinitionService,
        persistence_repo: WorkflowPersistenceRepository,
        ai_client: AbstractAIClient,  # Use the directly imported AbstractAIClient
    ) -> None:
        """
        Initialize the OrchestrationEngine.

        Args:
            definition_service: Service for loading and accessing workflow definitions.
            persistence_repo: Repository for saving and retrieving workflow instance state.
            ai_client: Client for interacting with the AI model.

        """
        self.definition_service = definition_service
        self.persistence_repo = persistence_repo
        self.ai_client = ai_client

    def list_workflows(self) -> list[str]:
        """Delegate to Definition Service to list available workflows."""
        try:
            return self.definition_service.list_workflows()
        except DefinitionServiceError as e:
            msg = f"Failed to list workflows: {e}"
            raise OrchestrationEngineError(msg) from e

    def start_workflow(
        self,
        workflow_name: str,
        initial_context: dict[str, Any] | None,
    ) -> StartWorkflowOutput:
        """Orchestrates starting a new workflow instance."""
        instance_id = str(uuid.uuid4())

        try:
            # Get the ordered list of steps from the definition service
            step_list = self.definition_service.get_step_list(workflow_name)

            # Select the first step from the list
            if not step_list:
                # This case should ideally be caught by definition service validation,
                # but handle defensively.
                msg = f"Workflow '{workflow_name}' has no steps defined."
                raise DefinitionParsingError(msg)  # Or a more specific engine error

            first_step_name = step_list[0]

            # Initial context is just the provided initial_context
            current_context = initial_context if initial_context else {}

            initial_state = WorkflowInstance(
                instance_id=instance_id,
                workflow_name=workflow_name,
                current_step_name=first_step_name,  # Use the first step from the list
                status="RUNNING",
                context=current_context,
                completed_at=None,
            )
            self.persistence_repo.create_instance(initial_state)

            # Get instructions for the first step
            instructions = self.definition_service.get_step_client_instructions(
                workflow_name,
                first_step_name,
            )

            return StartWorkflowOutput(
                instance_id=instance_id,
                next_step={
                    "step_name": first_step_name,
                    "instructions": instructions,
                },  # Use the first step name
                current_context=current_context,
            )

        except (DefinitionNotFoundError, DefinitionParsingError):
            raise
        except AIServiceError as e:
            msg = f"AI service error during workflow start: {e}"
            raise OrchestrationEngineError(msg) from e
        except PersistenceError as e:
            msg = f"Persistence error during workflow start: {e}"
            raise OrchestrationEngineError(msg) from e
        except Exception as e:
            msg = f"An unexpected error occurred during workflow start: {e}"
            raise OrchestrationEngineError(msg) from e

    def _validate_instance_state(
        self,
        instance: WorkflowInstance,
    ) -> AdvanceResumeWorkflowOutput | None:
        """Check if instance is already completed/failed and return final output if so."""
        if instance.status in ["COMPLETED", "FAILED"]:
            instructions = (
                "Workflow Completed."
                if instance.status == "COMPLETED"
                else "Workflow Failed."
            )
            last_step_name = (
                instance.current_step_name if instance.status == "FAILED" else "FINISH"
            )

            if instance.status == "COMPLETED":
                try:
                    instructions = self.definition_service.get_step_client_instructions(
                        instance.workflow_name,
                        "FINISH",
                    )
                    last_step_name = "FINISH"
                except DefinitionNotFoundError:
                    pass

            return AdvanceResumeWorkflowOutput(
                instance_id=instance.instance_id,
                next_step={"step_name": last_step_name, "instructions": instructions},
                current_context=instance.context if instance.context else {},
            )
        return None

    def _merge_contexts(
        self,
        base_context: dict[str, Any] | None,
        updates: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Safely merge two context dictionaries."""
        merged = base_context.copy() if base_context else {}
        if updates:
            merged.update(updates)
        return merged

    def _call_ai_for_advance(
        self,
        definition_blob: str,
        current_state: WorkflowInstance,
        report: ReportPayload,
    ) -> AIResponse:
        """Call the AI client to determine the next step for advance."""
        try:
            return self.ai_client.determine_next_step(
                definition_blob,
                current_state,
                report.model_dump(),
                None,
            )
        except AIServiceError as e:
            msg = f"AI service error determining next step for instance {current_state.instance_id}: {e}"
            raise OrchestrationEngineError(msg) from e

    def _call_ai_for_resume(
        self,
        definition_blob: str,
        persisted_state: WorkflowInstance,
        assumed_step: str,
        report: ReportPayload,
    ) -> AIResponse:
        """Call the AI client to reconcile and determine the next step for resume."""
        try:
            return self.ai_client.reconcile_and_determine_next_step(
                definition_blob,
                persisted_state,
                assumed_step,
                report.model_dump(),
                None,
            )
        except AIServiceError as e:
            msg = f"AI service error reconciling state for instance {persisted_state.instance_id}: {e}"
            raise OrchestrationEngineError(msg) from e

    def _update_and_persist_state(
        self,
        instance: WorkflowInstance,
        ai_response: AIResponse,
        current_context: dict[str, Any],
    ) -> tuple[WorkflowInstance, str]:
        """
        Determine new status, update instance object, and persist to DB.

        Returns the updated instance and the determined new status.
        """
        logger.info(
            "Determining new status for instance %s based on AI response: %s",
            instance.instance_id,
            ai_response,
        )
        new_status = instance.status  # Start with current status

        # Prioritize FINISH step for completion
        if ai_response.next_step_name == "FINISH":
            new_status = "COMPLETED"
            logger.info(
                "AI suggested FINISH step. Setting status to COMPLETED for instance %s.",
                instance.instance_id,
            )
        # Only consider status_suggestion if next_step_name is not FINISH
        elif ai_response.status_suggestion:
            if ai_response.status_suggestion in [
                "RUNNING",
                "SUSPENDED",
                "COMPLETED",
                "FAILED",
            ]:
                new_status = ai_response.status_suggestion
                logger.info(
                    "AI suggested valid status '%s'. Setting status for instance %s.",
                    new_status,
                    instance.instance_id,
                )
            else:
                logger.warning(
                    "AI suggested invalid status '%s' for instance %s. Ignoring.",
                    ai_response.status_suggestion,
                    instance.instance_id,
                )
                # Keep original status if suggestion is invalid

        logger.info(
            "Determined new status for instance %s: %s",
            instance.instance_id,
            new_status,
        )

        updated_state = WorkflowInstance(
            instance_id=instance.instance_id,
            workflow_name=instance.workflow_name,
            current_step_name=ai_response.next_step_name,
            status=new_status,
            context=current_context,  # Use the already merged context
            created_at=instance.created_at,
            completed_at=(
                datetime.now(timezone.utc)
                if new_status in ["COMPLETED", "FAILED"]
                else None
            ),
        )

        try:
            self.persistence_repo.update_instance(updated_state)
        except PersistenceError as e:
            msg = (
                f"Persistence error updating instance {instance.instance_id} state: {e}"
            )
            raise OrchestrationEngineError(msg) from e

        return updated_state, new_status

    def _get_next_step_instructions(
        self,
        instance: WorkflowInstance,  # Pass the potentially updated instance
        next_step_name: str,
    ) -> str:
        """Get instructions for the next step, handling potential errors."""
        logger.info(
            "Getting instructions for instance %s, step: %s (current status: %s)",
            instance.instance_id,
            next_step_name,
            instance.status,
        )
        if instance.status == "COMPLETED":  # Use instance status after update
            try:
                return self.definition_service.get_step_client_instructions(
                    instance.workflow_name,
                    "FINISH",
                )
            except DefinitionNotFoundError:
                return "Workflow Completed successfully."
        elif instance.status == "FAILED":
            # Should not typically request instructions for a FAILED state,
            # but provide a generic message if it happens.
            return "Workflow Failed."
        else:  # RUNNING or SUSPENDED
            try:
                return self.definition_service.get_step_client_instructions(
                    instance.workflow_name,
                    next_step_name,
                )
            except DefinitionNotFoundError as e:
                logger.exception(
                    "Invalid next step '%s' determined by AI for instance %s. Failing workflow.",
                    next_step_name,
                    instance.instance_id,
                )
                # Fail the workflow state as this is a critical error
                instance.status = "FAILED"
                instance.completed_at = datetime.now(timezone.utc)
                try:
                    self.persistence_repo.update_instance(instance)
                except PersistenceError:  # F841 Fix: Remove unused 'as pe'
                    logger.exception(
                        "Failed to update instance %s to FAILED after invalid step error.",  # PLE1206 Fix: Remove second %s
                        instance.instance_id,
                    )
                msg = f"AI determined invalid next step '{next_step_name}'. Workflow set to FAILED."
                raise OrchestrationEngineError(msg) from e
            except DefinitionParsingError as e:
                logger.exception(
                    "Error parsing instructions for step '%s' for instance %s. Failing workflow.",
                    next_step_name,
                    instance.instance_id,
                )
                # Fail the workflow state
                instance.status = "FAILED"
                instance.completed_at = datetime.now(timezone.utc)
                try:
                    self.persistence_repo.update_instance(instance)
                except PersistenceError:  # F841 Fix: Remove unused 'as pe'
                    logger.exception(
                        "Failed to update instance %s to FAILED after parsing error.",  # PLE1206 Fix: Remove second %s
                        instance.instance_id,
                    )
                msg = f"Error parsing instructions for step '{next_step_name}'. Workflow set to FAILED."
                raise OrchestrationEngineError(msg) from e

    def advance_workflow(
        self,
        instance_id: str,
        report: ReportPayload,
        context_updates: dict[str, Any] | None,
    ) -> AdvanceResumeWorkflowOutput:
        """Orchestrates advancing a workflow instance based on a step report."""
        logger.info(
            "Advancing workflow instance: %s with report: %s and context_updates: %s",
            instance_id,
            report,
            context_updates,
        )
        try:
            current_state: WorkflowInstance = self.persistence_repo.get_instance(
                instance_id
            )
            logger.info(
                "Retrieved current state for instance %s: %s",
                instance_id,
                current_state,
            )
            final_output = self._validate_instance_state(current_state)
            if final_output:
                logger.info(
                    "Instance %s already completed or failed. Returning final output.",
                    instance_id,
                )
                return final_output

            current_context = self._merge_contexts(
                current_state.context, context_updates
            )
            logger.info(
                "Merged initial context for instance %s: %s",
                instance_id,
                current_context,
            )

            history_entry = HistoryEntry(
                instance_id=instance_id,
                step_name=current_state.current_step_name,
                user_report=report.model_dump(),
                outcome_status=report.status,
            )
            self.persistence_repo.create_history_entry(history_entry)
            logger.info(
                "Created history entry for instance %s, step %s",
                instance_id,
                current_state.current_step_name,
            )

            definition_blob = self.definition_service.get_full_definition_blob(
                current_state.workflow_name
            )
            logger.info(
                "Calling AI client for instance %s with definition blob and current state.",
                instance_id,
            )
            ai_response = self._call_ai_for_advance(
                definition_blob, current_state, report
            )
            logger.info(
                "AI client response for instance %s: %s", instance_id, ai_response
            )

            # Merge AI context updates *before* updating state
            current_context = self._merge_contexts(
                current_context, ai_response.updated_context
            )
            logger.info(
                "Merged AI context updates for instance %s: %s",
                instance_id,
                current_context,
            )

            # Update state and persist
            logger.info(
                "Updating and persisting state for instance %s with AI response.",
                instance_id,
            )
            updated_state, new_status = self._update_and_persist_state(
                current_state,
                ai_response,
                current_context,
            )
            logger.info(
                "Updated state for instance %s: %s, new status: %s",
                instance_id,
                updated_state,
                new_status,
            )

            # Get instructions based on the *updated* state
            logger.info(
                "Getting next step instructions for instance %s, step: %s",
                instance_id,
                ai_response.next_step_name,
            )
            instructions = self._get_next_step_instructions(
                updated_state, ai_response.next_step_name
            )
            logger.info(
                "Instructions for instance %s, step %s: %s",
                instance_id,
                ai_response.next_step_name,
                instructions,
            )

            return AdvanceResumeWorkflowOutput(
                instance_id=instance_id,
                next_step={
                    "step_name": ai_response.next_step_name,
                    "instructions": instructions,
                },
                current_context=updated_state.context,  # Return context from the updated state
            )

        # Removed specific InstanceNotFoundError handler to allow generic wrapper below
        except (
            DefinitionServiceError,
            PersistenceError,
            AIServiceError,
            InstanceNotFoundError,
        ) as err:  # Add InstanceNotFoundError here
            logger.exception(
                "Error processing advance for instance %s: %s", instance_id, err
            )
            try:
                # Attempt to get state only if the error wasn't InstanceNotFoundError initially
                if not isinstance(err, InstanceNotFoundError):
                    state_to_fail = self.persistence_repo.get_instance(instance_id)
                    if state_to_fail.status not in ["COMPLETED", "FAILED"]:
                        state_to_fail.status = "FAILED"
                        state_to_fail.completed_at = datetime.now(timezone.utc)
                        if not isinstance(err, PersistenceError):
                            self.persistence_repo.update_instance(state_to_fail)
                        else:
                            logger.warning(
                                "Original error was PersistenceError for instance %s. Skipping FAILED status update.",
                                instance_id,
                            )
                else:
                    # Log that we can't update status because the instance wasn't found
                    logger.warning(
                        "Instance %s not found, cannot set status to FAILED.",
                        instance_id,
                    )

            except Exception:
                logger.exception(
                    "Failed to update instance %s to FAILED status after initial error.",
                    instance_id,
                )
                # The original code had a redundant update attempt here. Removed.

            msg = f"Error processing advance for instance {instance_id}: {err}"
            # RET506 Fix: Remove unnecessary else
            # The original code had an if/else that both raised the same exception type.
            # We can simplify this by just raising it once after the common message construction.
            raise OrchestrationEngineError(msg) from err

        except Exception as err:
            logger.exception(
                "An unexpected error occurred during workflow advance for instance %s: %s",
                instance_id,
                err,
            )
            msg = f"An unexpected error occurred during workflow advance for instance {instance_id}: {err}"
            try:
                state_to_fail = self.persistence_repo.get_instance(instance_id)
                if state_to_fail.status not in ["COMPLETED", "FAILED"]:
                    state_to_fail.status = "FAILED"
                    state_to_fail.completed_at = datetime.now(timezone.utc)
                    self.persistence_repo.update_instance(state_to_fail)
            except Exception:
                logger.exception(
                    "Failed to update instance %s to FAILED status after unexpected error.",
                    instance_id,
                )

            raise OrchestrationEngineError(msg) from err

    def resume_workflow(
        self,
        instance_id: str,
        assumed_step: str,
        report: ReportPayload,
        context_updates: dict[str, Any] | None,
    ) -> AdvanceResumeWorkflowOutput:
        """Orchestrates resuming a workflow instance with reconciliation."""
        try:
            persisted_state: WorkflowInstance = self.persistence_repo.get_instance(
                instance_id
            )
            final_output = self._validate_instance_state(persisted_state)
            if final_output:
                return final_output

            current_context = self._merge_contexts(
                persisted_state.context, context_updates
            )

            history_entry = HistoryEntry(
                instance_id=instance_id,
                step_name=assumed_step,
                user_report=report.model_dump(),
                outcome_status="RESUMING",
            )
            self.persistence_repo.create_history_entry(history_entry)

            definition_blob = self.definition_service.get_full_definition_blob(
                persisted_state.workflow_name
            )
            ai_response = self._call_ai_for_resume(
                definition_blob, persisted_state, assumed_step, report
            )

            # Merge AI context updates *before* updating state
            current_context = self._merge_contexts(
                current_context, ai_response.updated_context
            )

            # Update state and persist
            updated_state, new_status = self._update_and_persist_state(
                persisted_state,
                ai_response,
                current_context,  # Pass persisted_state as base
            )

            # Get instructions based on the *updated* state
            instructions = self._get_next_step_instructions(
                updated_state, ai_response.next_step_name
            )

            return AdvanceResumeWorkflowOutput(
                instance_id=instance_id,
                next_step={
                    "step_name": ai_response.next_step_name,
                    "instructions": instructions,
                },
                current_context=updated_state.context,  # Return context from the updated state
            )

        # Removed specific InstanceNotFoundError handler to allow generic wrapper below
        except (
            DefinitionServiceError,
            PersistenceError,
            AIServiceError,
            InstanceNotFoundError,
        ) as err:  # Add InstanceNotFoundError here
            try:
                # Attempt to get state only if the error wasn't InstanceNotFoundError initially
                if not isinstance(err, InstanceNotFoundError):
                    state_to_fail = self.persistence_repo.get_instance(instance_id)
                    if state_to_fail.status not in ["COMPLETED", "FAILED"]:
                        state_to_fail.status = "FAILED"
                        state_to_fail.completed_at = datetime.now(timezone.utc)
                        if not isinstance(err, PersistenceError):
                            self.persistence_repo.update_instance(state_to_fail)
                        else:
                            logger.warning(
                                "Original error was PersistenceError for instance %s. Skipping FAILED status update.",
                                instance_id,
                            )
                else:
                    # Log that we can't update status because the instance wasn't found
                    logger.warning(
                        "Instance %s not found, cannot set status to FAILED.",
                        instance_id,
                    )

            except Exception:
                logger.exception(
                    "Failed to update instance %s to FAILED status after initial error.",
                    instance_id,
                )
                if state_to_fail.status not in ["COMPLETED", "FAILED"]:
                    state_to_fail.status = "FAILED"
                    state_to_fail.completed_at = datetime.now(timezone.utc)
                    if not isinstance(err, PersistenceError):
                        self.persistence_repo.update_instance(state_to_fail)
                    else:
                        logger.warning(
                            "Original error was PersistenceError for instance %s. Skipping FAILED status update.",
                            instance_id,
                        )
            except Exception:
                logger.exception(
                    "Failed to update instance %s to FAILED status after initial error.",
                    instance_id,
                )

            msg = f"Error processing resume for instance {instance_id}: {err}"
            # RET506 Fix: Remove unnecessary else
            # Similar to the advance_workflow case, simplify the raise.
            raise OrchestrationEngineError(msg) from err

        except Exception as err:
            msg = f"An unexpected error occurred during workflow resume for instance {instance_id}: {err}"
            try:
                state_to_fail = self.persistence_repo.get_instance(instance_id)
                if state_to_fail.status not in ["COMPLETED", "FAILED"]:
                    state_to_fail.status = "FAILED"
                    state_to_fail.completed_at = datetime.now(timezone.utc)
                    self.persistence_repo.update_instance(state_to_fail)
            except Exception:
                logger.exception(
                    "Failed to update instance %s to FAILED status after unexpected error.",
                    instance_id,
                )
            raise OrchestrationEngineError(msg) from err

    def _get_current_time(self) -> datetime:
        """Get current UTC time."""
        return datetime.now(timezone.utc)
