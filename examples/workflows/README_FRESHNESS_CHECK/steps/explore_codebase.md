# Goal
Gather information about the codebase structure and implementation relevant to the README.md.

# Orchestrator Guidance
If the report indicates that codebase exploration is complete, proceed to "compare_and_identify_discrepancies".
If the report indicates a need for further exploration or clarification from the user, stay on this step.
If the report indicates failure, proceed to "report_failure".

# Client Instructions
Ask the user which directories or files to examine to verify the README.md's accuracy. Based on the user's response, use tools like `list_files`, `search_files`, or `read_file` to gather information. Report the gathered information or a summary in the `result` field of the `report` when calling `advance_workflow`. If the user provides guidance that requires further interaction or clarification, report that in the `result` and set the status to `data_provided`. If a tool use fails, report the error in the `error` field and set the status to `failure`. Once codebase exploration is complete based on user guidance, report a summary in the `result` and set the status to `success`.
