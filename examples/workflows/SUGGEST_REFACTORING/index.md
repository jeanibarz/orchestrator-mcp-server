# Goal
Identify and document refactoring opportunities in the codebase based on the KISS principle.

# Steps
*   [Read Codebase](steps/read_codebase.md)
*   [Identify Refactoring Opportunities](steps/identify_refactoring_opportunities.md)
*   [Write Refactoring Opportunities](steps/write_refactoring_opportunities.md)
*   [Double Check Refactoring Opportunities File](steps/double_check_refactoring_opportunities_file.md)
*   [Notify User Refactoring Opportunities](steps/notify_user_refactoring_opportunities.md)

# Error Handling
In case of any unexpected errors during a step, the client should stop the workflow and report the error to the user via the `ntfy-mcp` tool's `notify_user` function. The `taskTitle` should indicate an error occurred in the workflow, and the `taskSummary` should provide details about the error and the step where it occurred.
