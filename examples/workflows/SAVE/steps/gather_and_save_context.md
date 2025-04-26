# Goal
Collect all relevant information about the current task state and write it to `MEMORY_BANK/TASK_PROGRESS.md`.

# Orchestrator Guidance
- This is the first step in the save workflow.
- Success criteria: The current task state is successfully gathered and formatted.
- If successful, proceed to step 'Confirm Save And Query User'.
- If failure, report the error and transition to step 'Handle Save Error'.

# Client Instructions
- Identify the current workflow being executed (e.g., SPRINT_TASK). Store as `workflow_name`.
- Identify the last successfully completed step ID in that workflow. Store as `last_step_id`.
- Gather **all** relevant context variables (e.g., issue details, MR details if any, branch name, milestone, modified files, test status, next planned actions, any blocking issues). Store as `task_details`.
- **CRITICAL:** Format this information clearly within `MEMORY_BANK/TASK_PROGRESS.md`. Use Markdown formatting. Include enough detail so that an agent with no prior memory can understand the exact state and what needs to be done next. For example:
  ```markdown
  # Task Progress (Branch: {context.branch_name})

  **Workflow:** {context.workflow_name}
  **Last Completed Step:** {context.last_step_id}

  **Task Details:**
  *   Issue: #{context.issue_iid} - {context.issue_title}
  *   Milestone: {context.milestone_title}
  *   Status: [e.g., Implementation complete, tests failing on file X]
  *   Modified Files: {context.modified_files}
  *   ... (add any other relevant context variables) ...

  **Next Steps:**
  *   [Describe the immediate next action, e.g., "Fix test failures in tests/test_module.py"]
  *   [Describe subsequent steps]

  **Blockers:**
  *   [Describe any blocking issues]
  ```
- Use the `write_to_file` tool to overwrite `MEMORY_BANK/TASK_PROGRESS.md` with this detailed context.
- Report the path of the progress file in the context as `progress_file_path`.

# Context Expectations
- `workflow_name`: string (name of the current workflow)
- `last_step_id`: string (ID of the last completed step)
- `task_details`: object/string (all relevant context variables)
- `progress_file_path`: string (path to the saved progress file)
- `feedback_summary`: string (brief summary of the outcome)
- `error_details`: string (details if an error occurred)
- `struggle_indicator`: boolean (true if the step was difficult or required retries)
