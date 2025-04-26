# Goal
Read the content of all source code files in the project.

# Orchestrator Guidance
*   Proceed to the `identify_refactoring_opportunities` step.

# Client Instructions
1.  Identify all source code files in the project directory (excluding documentation, tests, and build artifacts). Focus on files within the `src/` directory.
2.  For each identified source file, read its content.
3.  Store the file paths and their content in the workflow context.

# Context Expectations
*   `source_code_files`: list of objects with `file_path` and `content` (Output: List of source file paths and their content.)
