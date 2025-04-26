# Goal
Read the content of the persistent task progress file.

# Orchestrator Guidance
- This is the first step in the resume workflow.
- Success criteria: The `MEMORY_BANK/TASK_PROGRESS.md` file is read successfully.
- If successful, proceed to Parse_And_Validate_Context.
- If failure, report the error and transition to Handle_Resumption_Decision with `is_resumable` set to false.

# Client Instructions
- Use the `read_file` tool to read the contents of `MEMORY_BANK/TASK_PROGRESS.md`.
- Report the content of the file in the context as `progress_content`.

# Context Expectations
- `progress_content`: string (content of the task progress file)
- `feedback_summary`: string (brief summary of the outcome)
- `error_details`: string (details if an error occurred)
- `struggle_indicator`: boolean (true if the step was difficult or required retries)
