# Goal
Update the README.md file based on the identified discrepancies.

# Orchestrator Guidance
If the report indicates that the README.md has been successfully refined, proceed to "validate_readme".
If the report indicates that user input is needed for refinement, stay on this step.
If the report indicates failure, proceed to "report_failure".

# Client Instructions
Present the identified discrepancies and proposed refinements (available in the workflow context from the "compare_and_identify_discrepancies" step) to the user. Ask for confirmation and specific instructions on how to update the README.md. Based on user feedback or the proposed refinements, use the `replace_in_file` or `write_to_file` tool to make the necessary changes to `README.md`. Report the outcome of the file modification in the `result` field of the `report` when calling `advance_workflow`. If user input is required, report the user's response in the `result` and set the status to `data_provided`. If a tool use fails, report the error in the `error` field and set the status to `failure`. Once the README.md has been successfully updated, report the success in the `result` and set the status to `success`.
