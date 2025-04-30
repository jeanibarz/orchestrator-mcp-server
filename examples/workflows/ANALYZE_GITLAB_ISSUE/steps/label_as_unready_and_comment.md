# Goal
Mark the issue as unready and inform the issue creator/assignees about the missing information.

# Orchestrator Guidance
This step receives the missing details from the the "Analyze Issue Detail" step. It should transition to the "Finish" step.

# Client Instructions
Use the `gitlab-issue` MCP server's `update_issue` tool to add the "unready" label. Use the `gitlab-issue` MCP server's `post_comment_to_issue` tool to add a comment listing the missing details and requesting clarification.
