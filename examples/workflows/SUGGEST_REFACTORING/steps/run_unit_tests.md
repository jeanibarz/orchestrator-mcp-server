# Goal
Execute the unit test suite for the project to verify the impact of the refactoring.

# Orchestrator Guidance
*   If `test_run_status` is "executed", proceed to the `analyze_test_results` step.
*   If `test_run_status` is "failed_to_execute", proceed directly to the `report_outcome` step.

# Client Instructions
1.  Navigate to the `project_path`.
2.  Execute the `test_command` in the terminal.
3.  Capture the complete output (stdout and stderr) and the exit code of the command.
4.  Report success if the command executed (regardless of test pass/fail status, which is analyzed next). Report failure if the command itself could not be run.

# Context Expectations
*   `project_path`: Path to the target project.
*   `test_command`: The command used to run the tests (e.g., `pytest`, `npm run test`).
*   `test_run_status`: string ("executed" if command ran, "failed_to_execute" otherwise.)
*   `test_exit_code`: number (On Success: The exit code of the test command.)
*   `test_output`: string (On Success: The full stdout/stderr from the test command.)
*   `error_message`: string (On Failure: Description of why the command failed (e.g., "Command not found").)
