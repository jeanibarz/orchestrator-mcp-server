# Goal
Determine if there are any files currently staged for commit.

# Orchestrator Guidance
If the client reports that the output contains "Changes to be committed:", proceed to "Get Staged Diffs".
If the client reports that the output does not contain "Changes to be committed:", proceed to "Handle No Staged Files".
If the client reports a failure, proceed to "Handle Failure".

# Client Instructions
Execute the command `git status`. Report the output of the command.
