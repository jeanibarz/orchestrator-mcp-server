# Goal
Inform the user that saving the task state failed.

# Orchestrator Guidance
- This is a terminal step that informs the user of a save error.
- Success criteria: The user is notified of the save failure.

# Client Instructions
- Use the `notify_user` tool to send a notification to the user.
- Set `taskTitle` to "Task Save Failed".
- Set `taskSummary` to "Failed to save the current task state. Please check the logs for details."

# Context Expectations
- None explicitly required for this step, but the error details from the previous step might be available in the context.
