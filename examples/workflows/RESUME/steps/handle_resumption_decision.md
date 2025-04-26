# Goal
Either trigger the continuation of the original workflow or inform the user if resumption is not possible.

# Orchestrator Guidance
- This is a terminal step that either resumes a workflow or prompts the user.
- Success criteria: The appropriate action is taken based on `is_resumable`.

# Client Instructions
- **If `{context.is_resumable}` is true:**
    - Use the `orchestrator-mcp-server` MCP tool (`advance_workflow`).
    - Provide the `current_step_id` as `{context.last_step_id}`.
    - Provide the `status` as 'success' (indicating the step saved *before* was successful).
    - Provide the `context` using the detailed `{context.task_details}` extracted in the previous step.
    - **Important:** Do *not* use the `trigger` parameter. The aim is to advance the original workflow (`{context.workflow_name}`).
    - Report the outcome returned by the `advance_workflow` call.
- **If `{context.is_resumable}` is false:**
    - Inform the user that `MEMORY_BANK/TASK_PROGRESS.md` is empty or does not contain actionable progress information for resumption.
    - Ask the user if a new task should be started using the `ask_followup_question` tool with options like ["Start new task (WORK)", "Do nothing"].
