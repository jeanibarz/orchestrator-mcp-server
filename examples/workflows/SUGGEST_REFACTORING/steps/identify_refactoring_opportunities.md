# Goal
Analyze the provided source code to identify 1 to 3 refactoring opportunities based on the KISS (Keep It Simple, Stupid) principle.

# Orchestrator Guidance
*   Proceed to the `write_refactoring_opportunities` step.

# Client Instructions
1.  Review the `source_code_files` from the context.
2.  Identify areas in the code that could be simplified, made more readable, or less complex, adhering to the KISS principle. Focus on practical improvements for a small project, avoiding over-engineering.
3.  Select between 1 and 3 distinct refactoring opportunities.
4.  For each opportunity, provide a clear description, the location in the code (file path and relevant lines), and a brief explanation of why it's a good refactoring candidate based on KISS.
5.  Store the identified opportunities in the workflow context.

# Context Expectations
*   `source_code_files`: list of objects with `file_path` and `content` (Input: List of source file paths and their content.)
*   `refactoring_opportunities`: list of objects with `description`, `location` (file_path and lines), and `reason` (Output: List of identified refactoring opportunities.)
