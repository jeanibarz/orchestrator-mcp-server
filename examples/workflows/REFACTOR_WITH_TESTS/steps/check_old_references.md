# Goal
Check for any remaining references to the `old_function_name` in the project after the initial refactoring step, excluding the function definition itself.

# Client Instructions
1. Use the `find_string.py` script to find all occurrences of the `old_function_name` within the `project_path` and files matching the `target_file_pattern`. Execute the script using the `execute_command` tool: `python scripts/find_string.py -p <project_path> -s <old_function_name> -f <target_file_pattern>`.
2. Analyze the output of the `find_string.py` script. For each found occurrence, determine if it falls within the line range of the function definition as specified in `function_locations`.
3. If any occurrences are found *outside* the function definition lines, consider them as remaining old references.
4. If remaining old references are found, prepare the output data with `old_references_found` set to `true` and populate `reference_locations` with the file path and line number of each such occurrence.
5. If no remaining old references are found, prepare the output data with `old_references_found` set to `false` and `reference_locations` as an empty list.

# Orchestrator Guidance
If `old_references_found` is true, transition to "Apply Rename Refactoring".
If `old_references_found` is false, transition to "Run Unit Tests".

# Context Expectations
*   `project_path`: string (Path to the target project.)
*   `target_file_pattern`: string (Glob pattern for relevant files, e.g., `*.py`.)
*   `old_function_name`: string (The function name to check for.)
*   `function_locations`: list of objects (Locations of the function definition, each containing `file_path` and `start_line`, and `end_line`.)
*   `old_references_found`: boolean (On Success: `true` if old references were found, `false` otherwise.)
*   `reference_locations`: list of objects (On Success: A list of objects, each containing `file_path` and `line_number` for each remaining old reference.)

# Next Steps
*   If `old_references_found` is `true`: [Apply Rename Refactoring](../apply_rename_refactoring.md)
*   If `old_references_found` is `false`: [Run Unit Tests](../run_unit_tests.md)
