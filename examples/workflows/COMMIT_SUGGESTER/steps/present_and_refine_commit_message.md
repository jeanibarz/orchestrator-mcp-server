# Goal
Present the suggested commit message to the user and allow refinement.

# Orchestrator Guidance
If the user approves the message, proceed to "Create Commit".
If the user cancels, proceed to "Handle User Cancellation".
If the user requests changes, stay on this step.
If the client reports a failure, proceed to "Handle Failure".

# Client Instructions
Ask the user if the suggested commit message is acceptable. If not, ask for their desired changes or a new message. Repeat this step until the user approves the message or cancels.
