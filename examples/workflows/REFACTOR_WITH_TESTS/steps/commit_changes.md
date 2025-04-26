# Goal
Commit the successfully refactored and tested code changes using the specified version control system.

# Orchestrator Guidance
*   Proceed to the `report_outcome` step, regardless of `commit_status` (failure should be reported).

# Client Instructions
1.  Navigate to the `project_path`.
2.  Use the specified `vcs_tool` to stage the `modified_files`.
    *   For `git`: `git add <file1> <file2> ...`
3.  Create a commit with a descriptive message.
    *   For `git`: `git commit -m "Refactor: Rename ${old_function_name} to ${new_function_name}"` (substitute variables).
4.  Verify that the commit command executed successfully.
5.  Report success or failure of the commit operation.

# Context Expectations
*   `project_path`: Path to the target project.
*   `modified_files`: List of file paths that were changed.
*   `vcs_tool`: Version control system used (e.g., 'git').
*   `old_function_name`: Original function name (for commit message).
*   `new_function_name`: New function name (for commit message).
*   `commit_status`: string ("success" if commit was successful, "failure" otherwise.)
*   `commit_hash`: string (optional: The hash of the new commit.)
*   `error_message`: string (On Failure: Description of why the commit failed.)
