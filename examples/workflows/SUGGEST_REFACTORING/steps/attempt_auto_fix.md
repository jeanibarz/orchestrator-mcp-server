# Goal
If tests failed due to predictable issues (like lingering references to `old_function_name` in test files), attempt to automatically fix them.

# Orchestrator Guidance
*   If `auto_fix_status` is "fix_attempted", proceed back to the `run_unit_tests` step to verify the fix.
*   If `auto_fix_status` is "fix_skipped" or "fix_failed", proceed to the `revert_changes` step.

# Client Instructions
1.  Analyze the `test_failure_summary`.
2.  Identify if the failures match patterns suitable for auto-fixing (e.g., `NameError` referencing `old_function_name` in test files).
3.  If fixable patterns are found:
    *   Locate the relevant lines in the test files (this might require searching test files specifically).
    *   Apply the necessary corrections (e.g., replace `old_function_name` with `new_function_name`).
    *   Save the modified test files.
    *   Report "fix_attempted".
4.  If no fixable patterns are found, or if fixing is disabled/not implemented, report "fix_skipped".
5.  If an error occurs during the fix attempt, report "fix_failed".

# Context Expectations
*   `project_path`: Path to the target project.
*   `test_failure_summary`: Summary of test failures.
*   `old_function_name`: The original function name.
*   `new_function_name`: The desired new function name.
*   `modified_files`: List of files modified during refactoring (potentially useful, but might need broader search).
*   `auto_fix_status`: string ("fix_attempted", "fix_skipped", or "fix_failed".)
*   `error_message`: string (if fix_failed: Description of the error.)
