# Goal
Analyze the README.md content and the codebase information to find inconsistencies or outdated instructions.

# Orchestrator Guidance
If the report indicates that discrepancies have been identified, proceed to "refine_readme".
If the report indicates no discrepancies were found, proceed to "validate_readme".
If the report indicates failure, proceed to "report_failure".

# Client Instructions
Compare the content of the README.md (available in the workflow context from the "read_readme" step) with the codebase information gathered in the "explore_codebase" step (also available in the context). Identify any instructions, examples, or descriptions in the README.md that are inaccurate, outdated, or could be improved based on the current codebase. Report the identified discrepancies and potential refinements in the `result` field of the `report` when calling `advance_workflow`. If no discrepancies are found, report that in the `result` and set the status to `success`. If an error occurs during the comparison, report the error in the `error` field and set the status to `failure`.
