# Goal
Notify the user that refactoring opportunities have been identified and provide a summary using the `ntfy-mcp` tool.

# Orchestrator Guidance
*   This is the final step of the workflow.

# Client Instructions
1.  Access the `refactoring_opportunities` from the context.
2.  Format a concise summary of the identified refactoring opportunities. Include the description and location for each opportunity.
3.  Use the `ntfy-mcp` server and the `notify_user` tool.
4.  Set the `taskTitle` to something like "Refactoring Opportunities Found".
5.  Set the `taskSummary` to the formatted summary of opportunities.

# Context Expectations
*   `refactoring_opportunities`: list of objects with `description`, `location` (file_path and lines), and `reason` (Input: List of identified refactoring opportunities.)
