Based on the codebase, to create a workflow, you need to create a specific directory structure and files that follow the workflow definition format used by the Workflow Definition Service.

For example, if you want to create a workflow named "MY_WORKFLOW", you would create:

```
workflows/
└── MY_WORKFLOW/
    ├── index.md              # Required: Overview and step list
    └── steps/                # Required: Directory containing step files
        ├── step1_name.md     # e.g., greet_user.md
        ├── step2_name.md
        └── ...
```

File Contents
1. index.md
The index.md file should contain:

An overall goal (optional)
A list of steps with links to the step files under a Level 1 Heading: `# Steps`
Optionally additional sections or instructions, that are ideally globally relevant independantly of the steps.

2. Step Files (in the steps/ directory)
Each step file must contain at least these two mandatory sections: `# Orchestrator Guidance` and `# Client Instructions`

Example of a step file content:
```markdown
# Goal
Greet the user and introduce the workflow.

# Orchestrator Guidance
If the user report indicates success, proceed to "Gather Task Details".
If the report indicates failure, stay on this step.

*Note: Orchestrator Guidance can define conditional transitions to different next steps based on the client's report. See the `ask_theme.md` and `handle_guess.md` examples in the "Complete Example: Joke Generator Workflow" section.*

# Client Instructions
Welcome to the workflow! Please introduce yourself and confirm you're ready to proceed.
```

*Note: Client Instructions can include references to context variables using `{{ context.variable }}` syntax and may instruct the client to update the context using the `context_updates` parameter when calling `advance_workflow`. See the `generate_joke.md` example in the "Complete Example: Joke Generator Workflow" section.*

Important Notes About Step Files
The filename (e.g., greet_user.md) is used to locate the content, but the canonical step ID comes from the link text in index.md.

You can include optional sections like `# Goal` or `# Context Expectations` for documentation.

The system supports file includes using the {{file:path}} syntax to reuse common content.

**Understanding Roles:** It is crucial to understand the distinct roles in this system for workflows to function correctly:

*   **User:** The end user who is interacting with the AI assistant (Client) through an MCP client application (like Claude Desktop).
*   **Client:** This is *you*, the AI assistant (e.g., ClaudeDev, Cline). Your role is to execute the workflow steps by following the `Client Instructions`, interact with the User as directed, and report the outcome back to the Orchestrator.
*   **Orchestrator:** The MCP server. Its role is to manage the workflow instance, interpret the workflow definition and the Client's reports (using an internal AI/LLM), and determine the *next* step for the Client to execute.

**Following Client Instructions:** The `# Client Instructions` section in each step file provides explicit directives for *you*, the AI Client. These instructions are not suggestions; they *must* be followed precisely to ensure the workflow progresses as intended and the correct information is gathered or actions are performed. Your ability to accurately execute these instructions and report the outcome is essential for the Orchestrator to determine the subsequent steps.

**Complete Example:**
Here's a complete example of a simple workflow `JOKE_GENERATOR`:

### workflows/JOKE_GENERATOR/index.md

```markdown
# Joke Workflow

This workflow greets the user, asks for a theme, and generates a joke.

# Steps

- [greet](steps/greet.md)
- [ask_theme](steps/ask_theme.md)
- [generate_joke](steps/generate_joke.md)
- [handle_guess](steps/handle_guess.md)
- [provide_answer](steps/provide_answer.md)
- [congratulations](steps/congratulations.md)
```

### workflows/JOKE_GENERATOR/steps/greet.md

```markdown
# Goal
Greet the user and ask for a joke theme.

# Orchestrator Guidance
Proceed "Ask for Joke Theme", unless told otherwise by the client.

# Client Instructions
Greet the user, asking if it is ready for a joke. For example: "Hello! I can tell you a joke. Are you ready?"
```

### workflows/JOKE_GENERATOR/steps/ask_theme.md

```markdown
# Goal
Ask the user for a theme for the joke.

# Orchestrator Guidance
If the user provides a theme in their report, proceed to "Generate Joke".
If the user does not provide a theme, stay on this step.

# Client Instructions
Asks the user what theme to use for the joke
```

### workflows/JOKE_GENERATOR/steps/generate_joke.md

```markdown
# Goal
Generate a joke (question and answer) based on the theme provided in the context (`context.theme`). Store both the question and answer in the context. Ask the user only the joke question.

# Orchestrator Guidance
Proceed to "Handle Guess".

# Client Instructions
1. Generate a complete joke (both question and answer) based on the theme: `{{ context.theme }}`.
2. When you call `advance_workflow` next, include the generated joke in the `context_updates` parameter. Use the keys `joke_question` for the question part and `joke_answer` for the answer part.
3. Ask the user *only* the joke question you generated. Do not reveal the answer yet.
```

### workflows/JOKE_GENERATOR/steps/handle_guess.md

```markdown
# Goal
Handle the user's guess for the joke's answer. The correct answer is available in the context (`context.joke_answer`).

# Orchestrator Guidance
If the user's guess is correct, proceed to "Congratulations".
If the user asks for the answer, proceed to "Provide Answer".
Otherwise, stay on this step to allow another guess.

# Client Instructions
Evaluate the user's guess against the correct answer found in `context.joke_answer`. If the guess is correct, inform the user and indicate success. If it is incorrect, inform the user and prompt for another guess. If the user indicates they want the answer, indicate that the answer will be provided.
```

### workflows/JOKE_GENERATOR/steps/provide_answer.md

```markdown
# Goal
Provide the answer to the joke, retrieving it from the context (`context.joke_answer`).

# Orchestrator Guidance
Proceed to "FINISH".

# Client Instructions
Retrieve the joke answer stored in `context.joke_answer` and provide it to the user.
```

### workflows/JOKE_GENERATOR/steps/congratulations.md

```markdown
# Goal
Congratulate the user on guessing the joke's answer.

# Orchestrator Guidance
Proceed to "FINISH".

# Client Instructions
Congratulate the user on guessing the joke's answer correctly.
```
