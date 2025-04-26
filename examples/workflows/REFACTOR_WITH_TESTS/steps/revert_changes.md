# Goal
Undo the code modifications made during the `Apply Rename Refactoring` step (and potentially `Attempt Auto Fix`) because tests failed and could not be automatically fixed.

# Orchestrator Guidance
*   Regardless of `revert_status` (though failure here is problematic), proceed to the `report_outcome` step to inform the user about the test failure and the revert attempt.

# Client Instructions
1.  Navigate to the `project_path`.
2.  Use the specified `vcs_tool` to revert the changes in the `modified_files`.
    *   For `git`, this would typically involve `git checkout -- <file1> <file2> ...`. Ensure all files in `modified_files` are included.
3.  Verify that the revert command executed successfully.
4.  Report success or failure of the revert operation.

# Context Expectations
*   `project_path`: Path to the target project.
*   `modified_files`: List of file paths that were changed during the refactoring and auto-fix attempts.
*   `vcs_tool`: Version control system used (e.g., 'git').
*   `revert_status`: string ("success" if revert was successful, "failure" otherwise.)
*   `error_message`: string (On Failure: Description of why the revert failed.)
