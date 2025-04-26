# Goal
Confirm state saving and ask the user for the next action.

# Orchestrator Guidance
- This is a terminal step that confirms saving and prompts the user.
- Success criteria: The user is informed and prompted for the next action.

# Client Instructions
- Confirm that the task state has been saved to `{context.progress_file_path}`.
- Ask the user whether to continue with the current task or stop. Use the `ask_followup_question` tool with options like ["Continue task", "Stop"].
