# Goal
Consolidate the results from previous steps and report the final outcome of the refactoring workflow.

# Orchestrator Guidance
*   This is typically the final step. The workflow instance should transition to a terminal state (Completed or Failed) **after** this step is reported as successfully performed.

# Client Instructions
1.  Analyze the status variables from the context (`locate_status`, `refactor_status`, `test_run_status`, `test_analysis_status`, `revert_status`, `commit_status`, etc.) to determine the overall workflow result.
2.  Construct a clear, concise summary message based on the outcome:
    *   **Success:** "Successfully refactored function '{old_function_name}' to '{new_function_name}'. Tests passed and changes committed (Commit: {commit_hash})."
    *   **Failure (Tests Failed, Reverted):** "Refactoring failed: Tests did not pass after renaming '{old_function_name}' to '{new_function_name}'. Changes have been reverted. Test failures: {test_failure_summary}." (Include revert status if it failed).
    *   **Failure (Tests Failed, Auto-Fix Failed, Reverted):** "Refactoring failed: Tests did not pass after renaming '{old_function_name}' to '{new_function_name}'. Auto-fix attempt failed ({auto_fix_status}). Changes have been reverted. Test failures: {test_failure_summary}."
    *   **Failure (Initial Step Failed):** "Refactoring failed: Could not {failed_step_description}. Error: {error_message}." (e.g., "Could not locate function", "Could not apply refactoring", "Could not execute test command").
    *   **Failure (Commit Failed):** "Refactoring completed and tests passed, but failed to commit changes for '{new_function_name}'. Error: {error_message}."
3.  Use the `use_mcp_tool` to notify the user of the outcome via the `ntfy-mcp` server.
    *   `server_name`: `ntfy-mcp`
    *   `tool_name`: `notify_user`
    *   `arguments`:
        ```json
        {
          "taskTitle": "Refactoring Workflow Outcome",
          "taskSummary": "{final_report}"
        }
        ```
4.  Output the final summary message.

# Context Expectations
*   `locate_status`: string (optional, from `locate_function`)
*   `refactor_status`: string (optional, from `apply_rename_refactoring`)
*   `test_run_status`: string (optional, from `run_unit_tests`)
*   `test_analysis_status`: string (optional, from `analyze_test_results`)
*   `test_failure_summary`: string (optional, if tests failed)
*   `auto_fix_status`: string (optional, from `attempt_auto_fix`)
*   `revert_status`: string (optional, from `revert_changes`)
*   `commit_status`: string (optional, from `commit_changes`)
*   `commit_hash`: string (optional, if committed)
*   `error_message`: string (optional, from various steps)
*   `old_function_name`: string
*   `new_function_name`: string
*   `final_report`: string (The generated summary message.)
*   `workflow_status`: string (Set to "Completed" or "Failed" based on the outcome.)
