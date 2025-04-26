# Goal
Determine the outcome of the unit tests based on the exit code and output captured in the previous step. Extract relevant failure information if tests did not pass.

# Orchestrator Guidance
*   If `test_analysis_status` is "passed", proceed to the `commit_changes` step.
*   If `test_analysis_status` is "failed", check workflow configuration/logic:
    *   If auto-fix is enabled/configured, proceed to `attempt_auto_fix`.
    *   Otherwise, proceed to the `revert_changes` step.

# Client Instructions
1.  Check the `test_exit_code`. Typically, an exit code of 0 indicates success, while non-zero indicates failure. (This might need adjustment based on the specific test runner).
2.  If the exit code indicates success, set the status to "passed".
3.  If the exit code indicates failure:
    *   Set the status to "failed".
    *   Parse the `test_output` to extract key information about the failures (e.g., names of failed tests, specific error messages or stack traces). Summarize this information concisely.
4.  Report the determined status and any extracted failure details.

# Context Expectations
*   `test_exit_code`: The exit code from the test command.
*   `test_output`: The stdout/stderr from the test command.
*   `test_analysis_status`: string ("passed" if tests passed, "failed" if tests failed.)
*   `test_failure_summary`: string (On Failure: A string containing summarized failure details (e.g., "Failed tests: test_old_name_reference. Errors: NameError: name 'old_function_name' is not defined").)
