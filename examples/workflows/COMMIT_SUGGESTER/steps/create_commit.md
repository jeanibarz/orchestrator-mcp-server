# Goal
Create the Git commit with the final message.

# Orchestrator Guidance
If the client reports success, proceed to "Finish".
If the client reports a failure, proceed to "Handle Failure".

# Client Instructions
Execute the command `git commit -m "{{ context.commit_message }}"` using the final approved commit message from the context.
