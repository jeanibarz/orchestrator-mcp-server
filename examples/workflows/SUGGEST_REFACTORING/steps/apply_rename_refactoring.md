# Goal
Rename the function identified in `function_locations` from `old_function_name` to `new_function_name`. This step should ideally perform a safe rename, updating references if possible, but a simple text replacement at the definition site is the minimum requirement.

# Orchestrator Guidance
*   If `refactor_status` is "success", proceed to the `check_old_references` step.
*   If `refactor_status` is "failure", proceed directly to the `report_outcome` step.

# Client Instructions
1.  Navigate to the `project_path`.
2.  For each location in `function_locations`:
    *   Open the specified `file_path`.
    *   Go to the `line_number`.
    *   Perform a targeted replacement of `old_function_name` with `new_function_name` specifically at the function definition site. Be careful not to accidentally replace other occurrences on the same line if possible. (More advanced agents could use AST manipulation or IDE refactoring tools if available).
    *   Save the modified file.
3.  Report success if all replacements were made, otherwise report failure.

# Context Expectations
*   `project_path`: Path to the target project.
*   `function_locations`: List of objects with `file_path` and `line_number` for the function definition.
*   `old_function_name`: The original function name.
*   `new_function_name`: The desired new function name.
*   `refactor_status`: string ("success" if refactoring was successful, "failure" otherwise.)
*   `modified_files`: list of strings (On Success: List of file paths that were changed.)
*   `error_message`: string (On Failure: Description of why the refactoring failed (e.g., "Could not modify file X").)
