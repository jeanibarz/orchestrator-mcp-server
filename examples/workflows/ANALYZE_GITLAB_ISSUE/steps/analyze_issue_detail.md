# Goal
Evaluate the retrieved issue content to determine if it contains enough information for assignment.

# Orchestrator Guidance
This step receives the issue details from the previous step. It needs to transition to either "Label as Ready" or "Label as Unready and Comment" based on the analysis result.

# Client Instructions
Analyze the issue title, description, and any comments for clarity, completeness, and necessary context. Determine if the issue is ready for someone to start working on it without further clarification. Report the analysis result (ready/unready) and any identified missing details in the result.
