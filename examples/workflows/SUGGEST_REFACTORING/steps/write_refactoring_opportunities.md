# Goal
Write the identified refactoring opportunities to the `docs/refactoring_opportunities` file, appending to the existing content if the file exists.

# Orchestrator Guidance
*   Proceed to the `double_check_refactoring_opportunities_file` step.

# Client Instructions
1.  Check if the file `docs/refactoring_opportunities` exists.
2.  If it exists, read its current content.
3.  Format the `refactoring_opportunities` from the context into a readable format (e.g., Markdown list). Include the description, location, and reason for each opportunity.
4.  Append the formatted new opportunities to the existing content (if any), adding a clear separator or heading if necessary.
5.  Write the combined content to `docs/refactoring_opportunities`.

# Context Expectations
*   `refactoring_opportunities`: list of objects with `description`, `location` (file_path and lines), and `reason` (Input: List of identified refactoring opportunities.)
