# Goal
Parse the content read from the file and determine if a task can be resumed.

# Orchestrator Guidance
- This step processes the content from the progress file.
- Success criteria: The content is parsed, and the resumability is determined.
- If `is_resumable` is true, proceed to Handle_Resumption_Decision.
- If `is_resumable` is false, proceed to Handle_Resumption_Decision.

# Client Instructions
- Analyze the `{context.progress_content}` read from `MEMORY_BANK/TASK_PROGRESS.md`.
- **CRITICAL:** Extract the original workflow name (e.g., `SPRINT_TASK`), the last successfully completed step ID, and all other relevant context details needed to continue. Store these as `workflow_name`, `last_step_id`, and `task_details` respectively.
- Determine if the content represents a valid, resumable state (i.e., contains necessary information like `workflow_name` and `last_step_id`).
- If the file is empty, lacks essential information, or indicates a completed task, set `is_resumable` to `false`.
- Otherwise, set `is_resumable` to `true`.
- Report `is_resumable`, `workflow_name`, `last_step_id`, and `task_details` in the context.

# Context Expectations
- `is_resumable`: boolean (true if the task can be resumed)
- `workflow_name`: optional string (name of the workflow to resume)
- `last_step_id`: optional string (ID of the last completed step)
- `task_details`: optional object/string (context needed to resume)
- `feedback_summary`: string (brief summary of the outcome)
- `error_details`: string (details if an error occurred)
- `struggle_indicator`: boolean (true if the step was difficult or required retries)
