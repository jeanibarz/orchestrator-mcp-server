# Goal
Safely refactor a specified function name within a target project, ensuring unit tests pass after the change. Handle test failures by attempting fixes or reverting changes.

# Steps
*   [Locate Function](steps/locate_function.md)
*   [Apply Rename Refactoring](steps/apply_rename_refactoring.md)
*   [Check for Old References](steps/check_old_references.md)
*   [Run Unit Tests](steps/run_unit_tests.md)
*   [Analyze Test Results](steps/analyze_test_results.md)
*   [Attempt Auto Fix](steps/attempt_auto_fix.md)
*   [Revert Changes](steps/revert_changes.md)
*   [Commit Changes](steps/commit_changes.md)
*   [Report Outcome](steps/report_outcome.md)

# Error Handling
Test failures are explicitly handled by branching to fix/revert steps. Other unexpected errors (e.g., file not found, command failure) should lead to a workflow failure state reported in `report_outcome`.
