"""Service class for loading, parsing, and validating workflow definitions."""

import hashlib
import logging
import os
import re
from pathlib import Path
from typing import Any, cast

from .models import (
    DefinitionNotFoundError,
    DefinitionParsingError,
    DefinitionServiceError,
)

# Import the logger setup
from .logger import setup_logger

# Set up module-level logger
logger = logging.getLogger(__name__)

# Setup the logger (will only configure handlers once)
setup_logger()


# Helper function to raise DefinitionParsingError consistently
# Defined at module level, so staticmethod decorator removed
def _raise_parsing_error(
    message: str, file_path: Path | None
) -> None:  # Mypy Fix: Removed @staticmethod
    """Raise a DefinitionParsingError with consistent formatting."""
    raise DefinitionParsingError(
        message, file_path=str(file_path) if file_path else None
    )


class WorkflowDefinitionService:
    """
    Service class for loading, parsing, and validating workflow definitions from Markdown files.

    Implements the conceptual AbstractDefinitionService interface.
    """

    def __init__(self, definitions_dir: str) -> None:
        """Initialize the WorkflowDefinitionService with the directory containing workflow definitions."""
        self.definitions_dir = definitions_dir
        # Cache for parsed workflow definitions
        self._workflow_cache: dict[str, dict[str, Any]] = {}
        # Cache for workflow directory checksums for invalidation
        self._checksum_cache: dict[str, str] = {}

        # Initial validation and caching of all workflows at startup
        self._load_all_workflows()

    def _load_all_workflows(self) -> None:
        """Attempt to load and validate all workflow definitions at startup."""
        definitions_path = Path(self.definitions_dir)
        if not definitions_path.is_dir():
            # Log warning if base definitions dir is missing
            logger.warning(
                "Definitions directory not found: %s", definitions_path
            )  # LOG015 Fix
            return

        workflow_names = [
            item.name for item in definitions_path.iterdir() if item.is_dir()
        ]

        for name in workflow_names:
            # Temporarily remove suppress to see the actual loading error
            # with contextlib.suppress(DefinitionNotFoundError, DefinitionParsingError, DefinitionServiceError):
            try:
                # Attempt to load and validate each workflow
                self._load_workflow(name)
            except (  # noqa: PERF203
                DefinitionNotFoundError,
                DefinitionParsingError,
                DefinitionServiceError,
            ) as e:
                # Log the error during initial load attempt
                logger.error(
                    "Failed to load workflow '%s' during initial scan: %s",
                    name,
                    e,
                    exc_info=True,
                )
                # Do not re-raise; allow service to initialize with valid workflows
                # raise e # Removed this line
            # Do not add invalid workflows to the cache (handled by _load_workflow raising exception)

    def _calculate_directory_checksum(self, workflow_name: str) -> str:
        """Calculate a checksum for a workflow directory based on file contents and names."""
        workflow_path = Path(self.definitions_dir) / workflow_name
        if not workflow_path.is_dir():
            return ""  # Directory doesn't exist

        checksum_hasher = hashlib.sha256()
        file_paths: list[Path] = []  # Add type hint for Mypy

        # Walk the directory and collect all file paths using list comprehension and extend (PERF401)
        file_paths.extend(
            Path(root) / file
            for root, _, files in os.walk(workflow_path)
            for file in files
        )

        # Sort file paths to ensure consistent checksum regardless of OS directory listing order
        file_paths.sort()

        for file_path in file_paths:
            # PERF203 Fix: Move try-except outside the inner read loop
            try:
                # Include file path relative to the workflow directory in the hash
                relative_path = file_path.relative_to(workflow_path)
                checksum_hasher.update(str(relative_path).encode("utf-8"))

                # Include file content in the hash
                with file_path.open("rb") as f:
                    # Syntax/Mypy Fix: Corrected indentation for while loop (one level)
                    while chunk := f.read(4096):
                        checksum_hasher.update(chunk)
            # Syntax Fix: Corrected indentation for except block
            except OSError as e:  # noqa: PERF203
                # Log error but continue; a failed read might invalidate the checksum anyway
                logger.warning(  # LOG015 Fix
                    "Could not read file %s during checksum calculation: %s",  # Syntax Fix: Corrected indentation
                    file_path,
                    e,
                    exc_info=False,  # Don't need full traceback for a warning
                )
                # To be safe, could raise an error here if any file read fails

        return checksum_hasher.hexdigest()

    def _is_cache_valid(self, workflow_name: str) -> bool:
        """Check if the cached workflow definition is up-to-date using checksum."""
        if workflow_name not in self._workflow_cache:
            return False  # Not in cache

        current_checksum = self._calculate_directory_checksum(workflow_name)
        cached_checksum = self._checksum_cache.get(workflow_name)

        return current_checksum == cached_checksum

    def _validate_workflow_paths(self, workflow_name: str) -> tuple[Path, Path, Path]:
        """Validate existence of workflow directory, index file, and steps directory."""
        workflow_path = Path(self.definitions_dir) / workflow_name
        index_file = workflow_path / "index.md"
        steps_dir = workflow_path / "steps"

        if not workflow_path.is_dir():
            msg = f"Workflow directory not found: {workflow_path}"
            raise DefinitionNotFoundError(msg, file_path=str(workflow_path))
        if not index_file.is_file():
            msg = f"Workflow index file not found: {index_file}"
            raise DefinitionNotFoundError(msg, file_path=str(index_file))
        if not steps_dir.is_dir():
            # Steps directory is required as per Section 8.1
            msg = f"Workflow steps directory not found: {steps_dir}"
            raise DefinitionNotFoundError(msg, file_path=str(steps_dir))

        return workflow_path, index_file, steps_dir

    def _parse_index_file(
        self,
        index_file: Path,
        workflow_path: Path,
    ) -> tuple[str, list[str], dict[str, str]]:
        """Parse the index.md file to extract steps and their paths."""
        try:
            with index_file.open(encoding="utf-8") as f:
                index_content_raw = f.read()
            index_content = self._resolve_includes(
                index_content_raw,
                str(index_file.parent),
                visited_files=[str(index_file)],
            )

            step_list: list[str] = []
            step_file_map: dict[str, str] = {}
            # Updated regex to match ordered (1.) or unordered (-, *, +) lists
            step_link_pattern = re.compile(
                r"^[ \t]*(\d+\.|[-*+]) [ \t]*\[([^\]]+)\]\(([^)]+\.md)\)",
                re.MULTILINE,
            )

            for line in index_content.splitlines():
                match = step_link_pattern.match(line)
                if match:
                    # Group 2 is now the step name, Group 3 is the path
                    step_name = match.group(2).strip()
                    relative_step_path = match.group(3).strip()

                    if not step_name or not relative_step_path:
                        continue

                    if step_name in step_file_map:
                        msg = f"Duplicate step name '{step_name}' found in workflow index file: {index_file}"
                        _raise_parsing_error(
                            msg, index_file
                        )  # TRY301/Mypy Fix: Call module-level function

                    step_list.append(step_name)
                    step_file_map[step_name] = str(
                        (workflow_path / relative_step_path).resolve(),
                    )

            if not step_list:
                msg = f"No steps found in workflow index file: {index_file}. Ensure steps are listed as Markdown links."
                _raise_parsing_error(
                    msg, index_file
                )  # TRY301/Mypy Fix: Call module-level function

        except DefinitionParsingError:
            raise
        except (OSError, FileNotFoundError) as e:
            msg = f"Error reading workflow index file or its includes: {e}"
            file_path_context = (
                e.filename if hasattr(e, "filename") else str(index_file)
            )  # Q000 fix
            raise DefinitionNotFoundError(msg, file_path=str(file_path_context)) from e
        except Exception as e:
            msg = f"An unexpected error occurred while parsing index file '{index_file}': {e}"
            raise DefinitionServiceError(msg) from e
        else:
            # TRY300: Successful return only if no exceptions occurred
            return index_content, step_list, step_file_map

    # C901 Refactoring: Extracted section parsing logic
    def _extract_step_sections(
        self, step_content: str
    ) -> tuple[str | None, str | None]:
        """Extract Orchestrator Guidance and Client Instructions sections from step content."""
        orchestrator_guidance = None
        client_instructions = None

        # Define markers and their corresponding keys
        markers = {
            "# Orchestrator Guidance": "orchestrator_guidance",
            "# Client Instructions": "client_instructions",
            # Add other potential section markers here if needed in the future
        }

        # Find all marker occurrences and their positions
        found_sections = []
        for marker_text, key in markers.items():
            # Regex to find the marker at the start of a line, ignoring leading whitespace
            # and case for the marker text itself.
            pattern = re.compile(
                rf"^[ \t]*{re.escape(marker_text)}[ \t]*$", re.MULTILINE | re.IGNORECASE
            )
            for match in pattern.finditer(step_content):
                # Store start position of the line containing the marker,
                # end position of the marker line, and the key
                marker_line_start = match.start()
                marker_line_end = match.end()
                found_sections.append((marker_line_start, marker_line_end, key))

        # Sort sections by their starting position
        found_sections.sort(key=lambda x: x[0])

        # Extract content between markers
        extracted_content = {}
        for i, (current_marker_start, current_marker_end, current_key) in enumerate(
            found_sections
        ):
            # Content starts after the current marker line ends
            content_start = current_marker_end
            # Content ends at the start of the next marker line, or end of file if it's the last marker
            content_end = (
                found_sections[i + 1][0]
                if i + 1 < len(found_sections)
                else len(step_content)
            )

            # Extract and strip whitespace
            content = step_content[content_start:content_end].strip()
            extracted_content[current_key] = content

        orchestrator_guidance = extracted_content.get("orchestrator_guidance")
        client_instructions = extracted_content.get("client_instructions")

        return orchestrator_guidance, client_instructions

    def _parse_step_file(self, step_file_path: Path) -> dict[str, str]:
        """
        Parse a single step file, resolve includes, extract and validate required sections.

        Args:
            step_file_path: The absolute path to the step file.

        Returns:
            A dictionary containing:
                - "orchestrator_guidance": The extracted guidance text.
                - "client_instructions": The extracted instructions text.
                - "full_content": The fully resolved content of the step file.

        Raises:
            DefinitionNotFoundError: If the step file or its includes are not found.
            DefinitionParsingError: If mandatory sections are missing or includes are circular/too deep.
            DefinitionServiceError: For unexpected errors during parsing or include resolution.

        """  # D413 fix - Added blank line above
        if not step_file_path.is_file():
            # This check should ideally be redundant if called correctly, but good safeguard
            msg = f"Step file does not exist: {step_file_path}"
            raise DefinitionNotFoundError(msg, file_path=str(step_file_path))

        try:
            # Read step file and resolve includes
            with step_file_path.open(encoding="utf-8") as f:
                step_content_raw = f.read()
            step_content = self._resolve_includes(
                step_content_raw,
                str(step_file_path.parent),
                visited_files=[str(step_file_path)],  # Start new visited list
                depth=0,
            )

            # C901 Fix: Call extracted helper method
            orchestrator_guidance, client_instructions = self._extract_step_sections(
                step_content
            )
            full_content_for_blob = (
                step_content  # Use resolved content (includes markers)
            )

            # --- Step Validation ---
            # Use the header markers for error messages
            guidance_marker_err = "# Orchestrator Guidance"
            instructions_marker_err = "# Client Instructions"

            if orchestrator_guidance is None or not orchestrator_guidance:
                msg = f"Mandatory '{guidance_marker_err}' section not found or is empty in step file: {step_file_path}"
                _raise_parsing_error(msg, step_file_path)  # TRY301 Fix
            if client_instructions is None or not client_instructions:
                msg = f"Mandatory '{instructions_marker_err}' section not found or is empty in step file: {step_file_path}"
                _raise_parsing_error(msg, step_file_path)  # TRY301 Fix

        except DefinitionParsingError:
            raise  # Re-raise specific parsing errors (e.g., from includes or missing sections)
        except (OSError, FileNotFoundError) as e:
            # Convert file read errors during step parsing to DefinitionNotFoundError
            msg = f"Error reading step file or its includes: {e}"
            file_path_context = (
                e.filename if hasattr(e, "filename") else str(step_file_path)
            )  # Q000 fix
            raise DefinitionNotFoundError(msg, file_path=str(file_path_context)) from e
        except Exception as e:
            # Catch any other unexpected errors during step parsing
            msg = f"An unexpected error occurred while parsing step file '{step_file_path}': {e}"
            raise DefinitionServiceError(msg) from e
        else:
            # TRY300: Successful return only if no exceptions occurred
            # Mypy Fix: Use cast to assure non-None types after validation checks
            # Asserts removed as cast serves the purpose for Mypy
            return {
                "orchestrator_guidance": cast("str", orchestrator_guidance),
                "client_instructions": cast("str", client_instructions),
                "full_content": full_content_for_blob,
            }

    def _load_workflow(self, workflow_name: str) -> dict[str, Any]:
        """Load, parse, and validate a single workflow definition. (Refactored)."""  # D400/D415 fix - Added period
        # Check cache validity first
        if self._is_cache_valid(workflow_name):
            return self._workflow_cache[workflow_name]

        # --- Path Validation ---
        # TRY203 Fix: Remove redundant try-except-raise block
        _, index_file, _ = self._validate_workflow_paths(workflow_name)
        workflow_path = (
            index_file.parent
        )  # Get workflow path from validated index file path

        # --- Index Parsing ---
        # TRY203 Fix: Remove redundant try-except-raise block
        index_content, step_list, step_file_map = self._parse_index_file(
            index_file, workflow_path
        )
        full_blob_parts = [index_content]  # Start blob with resolved index content

        # --- Step Parsing ---
        try:
            parsed_steps: dict[str, dict[str, str]] = {}
            for step_name in step_list:
                step_file_path = Path(
                    step_file_map[step_name]
                )  # Path is already absolute and resolved
                # Parse the individual step file
                step_data = self._parse_step_file(step_file_path)
                parsed_steps[step_name] = (
                    step_data  # Store guidance, instructions, full_content
                )

                # Add the step's full resolved content to the blob parts
                full_blob_parts.append(
                    f"## Step: {step_name}\n\n{step_data['full_content']}",
                )

            # Assemble the full definition blob
            full_definition_blob = "\n\n---\n\n".join(full_blob_parts)

            # --- Caching ---
            cached_data = {
                "step_list": step_list,
                "parsed_steps": parsed_steps,  # Contains guidance/instructions/full_content per step
                "full_definition_blob": full_definition_blob,
            }
            self._workflow_cache[workflow_name] = cached_data
            self._checksum_cache[workflow_name] = self._calculate_directory_checksum(
                workflow_name,
            )

        except (
            DefinitionNotFoundError,
            DefinitionParsingError,
            DefinitionServiceError,
        ):
            # Re-raise errors encountered during step parsing
            raise  # TRY201 fix - Simplified raise
        except Exception as e:
            # Catch any other unexpected errors during step parsing loop
            msg = f"An unexpected error occurred while processing steps for workflow '{workflow_name}': {e}"
            raise DefinitionServiceError(msg) from e
        else:
            # TRY300: Successful return only if no exceptions occurred
            # Add logging for loaded workflow and its steps
            logger.info(f"Loaded workflow '{workflow_name}' with steps: {step_list}")
            return cached_data

    def _resolve_includes(
        self,
        content: str,
        base_dir: str,
        visited_files: list[str] | None = None,
        depth: int = 0,
    ) -> str:
        """Recursively resolve {{file:path}} includes."""
        if visited_files is None:
            visited_files = []

        max_include_depth = 10
        if depth > max_include_depth:
            msg = f"Maximum include depth ({max_include_depth}) exceeded."
            raise DefinitionParsingError(
                msg,
                file_path=visited_files[-1] if visited_files else None,
            )  # Report last visited file

        include_pattern = re.compile(r"\{\{file:([^}]+)\}\}")
        resolved_content = content
        # Find all matches first to avoid modification issues during iteration
        matches = list(include_pattern.finditer(resolved_content))

        # Process matches from end to start to avoid issues with index changes
        for match in reversed(matches):
            include_path_relative = match.group(1).strip()
            if not include_path_relative:
                continue  # Skip empty include paths

            # Resolve the include path relative to the current file's directory
            include_file_path = (Path(base_dir) / include_path_relative).resolve()

            if str(include_file_path) in visited_files:
                msg = f"Circular include detected: {include_file_path} already visited in chain {visited_files}."
                raise DefinitionParsingError(msg, file_path=str(include_file_path))

            if not include_file_path.is_file():
                msg = f"Included file not found: {include_file_path} (referenced in {visited_files[-1] if visited_files else base_dir})"
                raise DefinitionParsingError(
                    msg,
                    file_path=str(include_file_path),
                )  # Treat missing include as parsing error

            try:
                with include_file_path.open(encoding="utf-8") as f:
                    included_content = f.read()

                # Recursively resolve includes in the included content
                nested_visited_files = [*visited_files, str(include_file_path)]
                resolved_included_content = self._resolve_includes(
                    included_content,
                    str(include_file_path.parent),
                    nested_visited_files,
                    depth + 1,
                )

                # Replace the include tag with the resolved content
                resolved_content = (
                    resolved_content[: match.start()]
                    + resolved_included_content
                    + resolved_content[match.end() :]
                )

            except (OSError, FileNotFoundError) as e:
                # This might be redundant if the is_file check catches it, but keep for robustness
                msg = f"Error reading included file: {e}"
                raise DefinitionNotFoundError(
                    msg, file_path=str(include_file_path)
                ) from e
            except DefinitionParsingError:
                raise  # Re-raise specific parsing errors from nested calls
            except Exception as e:
                # Catch unexpected errors during include resolution
                msg = f"An unexpected error occurred while resolving include '{include_path_relative}' in '{base_dir}': {e}"
                raise DefinitionServiceError(msg) from e

        return resolved_content

    def list_workflows(self) -> list[str]:
        """List the names of all available workflow definitions."""
        # Return names of workflows successfully loaded into the cache
        return list(self._workflow_cache.keys())

    def get_full_definition_blob(self, workflow_name: str) -> str:
        """Return the pre-assembled text blob for the specified workflow."""
        workflow_data = self._load_workflow(workflow_name)  # Ensures loaded/validated
        return workflow_data["full_definition_blob"]

    def get_step_client_instructions(self, workflow_name: str, step_name: str) -> str:
        """Return the verbatim client instructions for the specified step."""
        workflow_data = self._load_workflow(workflow_name)  # Ensures loaded/validated
        parsed_steps = workflow_data["parsed_steps"]
        if step_name not in parsed_steps:
            msg = f"Step '{step_name}' not found in workflow '{workflow_name}'."
            # Use DefinitionNotFoundError as step is part of the definition
            raise DefinitionNotFoundError(
                msg
            )  # No specific file path for missing step in loaded data
        # Access the nested dictionary correctly
        return parsed_steps[step_name]["client_instructions"]

    def get_step_list(self, workflow_name: str) -> list[str]:
        """Return the ordered list of canonical step names for the workflow."""
        workflow_data = self._load_workflow(workflow_name)  # Ensures loaded/validated
        return workflow_data["step_list"]

    def validate_workflow(self, workflow_name: str) -> bool:
        """
        Explicitly trigger validation for a workflow.

        Loading the workflow implicitly validates it.
        This method just needs to call _load_workflow and return True if no exception is raised.
        """
        # Loading the workflow implicitly validates it by calling _load_workflow.
        # If _load_workflow succeeds without raising an exception, validation passes.
        self._load_workflow(
            workflow_name
        )  # Let exceptions propagate if validation fails
        return True


# Example usage (for testing)
if __name__ == "__main__":
    # Local import for example usage
    from pathlib import Path

    # Ensure the environment variable is set before creating the service instance
    definitions_path_str = os.environ.get("WORKFLOW_DEFINITIONS_DIR", "../../workflows")
    definitions_path = Path(definitions_path_str).resolve()  # Resolve path for clarity
    # ERA001 Removed: # print(f"Attempting to load definitions from: {definitions_path}") # T201 Removed

    if not definitions_path.is_dir():
        # ERA001 Removed: # print(f"Error: Definitions directory not found at {definitions_path}") # T201 Removed
        pass  # Added pass as block needs content
    else:
        try:
            service = WorkflowDefinitionService(str(definitions_path))
            # ERA001 Removed: # print("WorkflowDefinitionService initialized.") # T201 Removed
            available_workflows = service.list_workflows()
            # ERA001 Removed: # print(f"Available workflows: {available_workflows}") # T201 Removed
            for wf_name in available_workflows:
                # ERA001 Removed: # print(f"\nValidating workflow: {wf_name}") # T201 Removed
                try:
                    is_valid = service.validate_workflow(wf_name)
                    # ERA001 Removed: # print(f"Validation result for {wf_name}: {'Success' if is_valid else 'Failed'}") # T201 Removed
                    # ERA001 Removed: # Example: Get step list (ERA001 Removed)
                    # ERA001 Removed: # step_list = service.get_step_list(wf_name)
                    # ERA001 Removed: # print(f"Steps for {wf_name}: {step_list}") # ERA001 Removed
                except (  # noqa: PERF203
                    DefinitionNotFoundError,
                    DefinitionParsingError,
                    DefinitionServiceError,
                ) as e:
                    # ERA001 Removed: # print(f"Validation FAILED for {wf_name}: {e}") # T201 Removed
                    if hasattr(e, "file_path") and e.file_path:  # Q000 fix
                        pass

        except (
            DefinitionNotFoundError,
            DefinitionParsingError,
            DefinitionServiceError,
        ) as e:
            # ERA001 Removed: # print(f"\nError during service initialization: {e}") # T201 Removed
            if hasattr(e, "file_path") and e.file_path:  # Q000 fix
                # ERA001 Removed: # print(f"Problematic file: {e.file_path}") # T201 Removed
                pass  # Added pass as block needs content
        # ERA001 Removed: # BLE001: Catching specific errors above, avoid blind except Exception
        # ERA001 Removed: # except Exception as e:
        # ERA001 Removed: #      print(f"\nAn unexpected error occurred during initialization: {e}") # T201 Removed
