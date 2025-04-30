# Goal
Obtain the current content of the README.md file.

# Orchestrator Guidance
If the report indicates success, proceed to "explore_codebase".
If the report indicates failure, proceed to "report_failure".
If the report indicates a need for clarification or data from the user, stay on this step.

# Client Instructions
Use the `read_file` tool with the path `README.md`. Report the file content in the `result` field of the `report` when calling `advance_workflow`. If the tool use fails, report the error in the `error` field and set the status to `failure`.
