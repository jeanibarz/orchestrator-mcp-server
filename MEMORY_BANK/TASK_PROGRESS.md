# Task Progress: Run tests and fix remaining issues

**Current Status:** Task interrupted by user SAVE command. Tests are currently failing.

**Remaining Failures:**
- `tests/unit/test_engine.py::test_start_workflow_handles_definition_not_found`: `AttributeError: 'function' object has no attribute 'create_instance'`
- `tests/unit/test_engine.py::test_start_workflow_handles_ai_error`: `AssertionError: Expected 'get_step_list' to be called once. Called 2 times.`
- `tests/unit/test_engine.py::test_start_workflow_handles_persistence_error`: `AssertionError: Expected 'determine_first_step' to not have been called. Called 1 times.`
- `tests/unit/test_server.py::test_get_workflow_status_instance_not_found`: `AssertionError: assert "Instance 'non-existent-id' not found" in "An unexpected error occurred while getting status for instance 'non-existent-id'."`

**Work Completed So Far:**
- Ran initial tests using `./run_tests.sh`.
- Identified 6 failing tests.
- Modified `tests/unit/test_engine.py` to align expected first step names in `test_start_workflow_success_no_initial_context` and `test_start_workflow_success_with_initial_context` with the mocked definition service's return value ("Step 1").
- Modified `src/orchestrator_mcp_server/engine.py` to merge the AI's `updated_context` into the initial context in the `start_workflow` method.
- Added the `mock_ai_client` fixture to the `test_start_workflow_handles_definition_not_found` test function signature.
- Corrected assertions in `test_start_workflow_handles_ai_error` and `test_start_workflow_handles_persistence_error` based on the perceived execution flow.

**Next Steps:**
1. Fix the `AttributeError` in `test_start_workflow_handles_definition_not_found` by adding the `mock_persistence_repo` fixture to the test function signature.
2. Re-examine the `test_start_workflow_handles_ai_error` and `test_start_workflow_handles_persistence_error` tests and the `start_workflow` method in `src/orchestrator_mcp_server/engine.py` to understand the incorrect assertion failures that are still occurring.
3. Fix the `test_get_workflow_status_instance_not_found` test in `tests/unit/test_server.py` and the corresponding error handling in `src/orchestrator_mcp_server/server.py` to return a more specific error message.
4. Rerun tests and repeat until all pass.
5. Use `attempt_completion` to report the successful test run.
