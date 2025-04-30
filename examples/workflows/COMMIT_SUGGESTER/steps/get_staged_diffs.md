# Goal
Get the diff content of staged files.

# Orchestrator Guidance
If the client reports success, proceed to "Suggest Commit Message".
If the client reports a failure, proceed to "Handle Failure".

# Client Instructions
Execute the command `git diff --cached > staged_diff.txt` to output diffs to a file. Then read the content of `staged_diff.txt`. Report the content of `staged_diff.txt`.
