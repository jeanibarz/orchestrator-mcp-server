# Goal
Generate a joke (question and answer) based on the theme provided in the context (`context.theme`). Store both the question and answer in the context. Ask the user only the joke question.

# Orchestrator Guidance
Proceed to "Handle Guess".

# Client Instructions
1. Generate a complete joke (both question and answer) based on the theme: `{{ context.theme }}`.
2. When you call `advance_workflow` next, include the generated joke in the `context_updates` parameter. Use the keys `joke_question` for the question part and `joke_answer` for the answer part.
3. Ask the user *only* the joke question you generated. Do not reveal the answer yet.
