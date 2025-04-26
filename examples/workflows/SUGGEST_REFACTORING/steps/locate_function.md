# Goal
Identify the exact file path(s) and line numbers where the `old_function_name` is defined within the specified `project_path` and `target_file_pattern`.

# Orchestrator Guidance
*   If `locate_status` is "success", proceed to the `Apply Rename Refactoring` step.
*   If `locate_status` is "failure", proceed directly to the `Report Outcome` step, indicating the failure reason.

# Client Instructions
1.  To locate the definition of the `old_function_name`, you can use the `find_function.py` helper script located in the current working directory (`/home/jean/git/mcp-tools/orchestrator-mcp-server`).
    *   Execute the script using the `execute_command` tool with the function name and project path: `python scripts/find_function.py <old_function_name> <project_path>`. If a specific file pattern is needed, use the `-f` argument: `python scripts/find_function.py <old_function_name> <project_path> -f <target_file_pattern>`.
    *   Analyze the output of the script to identify the file path(s) and line number(s) where the function is defined.
2.  Alternatively, you can utilize the `search_files` tool to locate the definition of the `old_function_name` within the `project_path` and files matching the `target_file_pattern`. A suitable regex pattern should target function definitions (e.g., `^def\s+<old_function_name>\s*\(` for Python). Ensure the regex is robust enough to account for variations in spacing or potential decorators.
3.  Carefully analyze the results from either method to identify the precise file path(s) and the start and end line numbers of the function definition(s). Pay close attention to accurately extracting line numbers from the tool's output format.
4.  If no definition is found, report the step as a failure with an appropriate error message.
5.  If one or more definitions are found, prepare the output data in the specified `function_locations` format. If multiple definitions are found, include all of them in the list.

# Context Expectations
*   `project_path`: string (Path to the target project.)
*   `target_file_pattern`: string (Glob pattern for relevant files, e.g., `*.py`.)
*   `old_function_name`: string (The function name to locate.)
*   `function_locations`: list of objects (On Success: A list of objects, each containing `file_path`, `start_line`, and `end_line`. These should represent the precise location of the function definition. Example: `[{"file_path": "src/module.py", "start_line": 42, "end_line": 50}]`)
*   `locate_status`: string ("success" if found, "failure" if not found.)
*   `error_message`: string (On Failure: "Function definition not found.")
