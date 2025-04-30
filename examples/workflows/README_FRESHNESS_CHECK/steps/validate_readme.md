# Goal
Re-read the README.md to ensure its content is as expected after refinement.

# Orchestrator Guidance
If the report indicates that the README.md content is valid, proceed to "confirm_completion".
If the report indicates that the README.md content is invalid, proceed to "report_failure".
If the report indicates failure, proceed to "report_failure".

# Client Instructions
Use the `read_file` tool with the path `README.md` to get the latest content. Compare this content with the expected content based on the refinements made in the previous step. Report the outcome of the validation in the `result` field of the `report` when calling `advance_workflow`. If the content is valid, set the status to `success`. If the content is invalid, report the discrepancies found and set the status to `failure`. If a tool use fails, report the error in the `error` field and set the status to `failure`.
