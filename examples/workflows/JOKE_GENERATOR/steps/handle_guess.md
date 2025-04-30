# Goal
Handle the user's guess for the joke's answer. The correct answer is available in the context (`context.joke_answer`).

# Orchestrator Guidance
If the user's guess is correct, proceed to "Congratulations".
If the user asks for the answer, proceed to "Provide Answer".
Otherwise, stay on this step to allow another guess.

# Client Instructions
Evaluate the user's guess against the correct answer found in `context.joke_answer`. If the guess is correct, inform the user and indicate success. If it is incorrect, inform the user and prompt for another guess. If the user indicates they want the answer, indicate that the answer will be provided.
