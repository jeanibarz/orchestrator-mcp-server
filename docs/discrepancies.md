# Discrepancies Between Architecture Document and Implementation

This document outlines the discrepancies found between the architecture document (`docs/architecture_and_data_model.md`) and the actual implementation of the Orchestrator MCP Server.

## Summary
The implementation generally follows the architecture described in the document, but there are a few remaining discrepancies that need to be addressed.

## 4. Workflow Definition Service Validation

### Architecture Document (Section 8.3)
The document specifies that the service must perform these validations when loading a workflow definition:
- Check existence of the workflow subdirectory
- Check existence and readability of `index.md`
- Check if `index.md` contains a list linking to step files
- For each step listed in `index.md`:
  - Check if the linked step file exists and is readable
  - Check if the step file contains the mandatory `# Orchestrator Guidance` section header
  - Check if the step file contains the mandatory `# Client Instructions` section header
- Check for duplicate Step IDs (link text) in `index.md`

### Actual Implementation
The implementation in `definition_service.py` performs most of these validations but with some differences:

1. The validation for duplicate Step IDs is performed during index parsing, not as a separate validation step:
```python
if step_name in step_file_map:
    msg = f"Duplicate step name '{step_name}' found in workflow index file: {index_file}"
    _raise_parsing_error(msg, index_file)
```

2. The validation for section headers in step files uses a more flexible approach that ignores case and whitespace:
```python
pattern = re.compile(rf"^[ \t]*{re.escape(marker_text)}[ \t]*$", re.MULTILINE | re.IGNORECASE)
```

This means that variations like `# orchestrator guidance` or `#   Orchestrator Guidance  ` would be accepted, which is more lenient than what might be implied by the architecture document.

## 5. Current Step Name Nullability

### Architecture Document (Section 3.3)
The SQL schema for the `workflow_instances` table defines `current_step_name` as `NOT NULL`:
```sql
current_step_name TEXT NOT NULL
```

### Actual Implementation
In the `WorkflowInstance` model (`models.py`), `current_step_name` is defined as nullable:
```python
current_step_name: str | None = Field(
    ...,
    description="The name of the last step determined by the orchestrator (can be None initially).",
)
```

However, the database schema in `database.py` correctly implements the NOT NULL constraint:
```python
current_step_name TEXT NOT NULL
```

This discrepancy could lead to runtime errors if the model allows None but the database doesn't.

## 9. Workflow Definition File Includes

### Architecture Document (Section 8)
The document mentions file includes in Section 8.4:
```
The parser supports including content from other files using the {{file:path}} syntax within both index.md and step files.
```

### Actual Implementation
The implementation in `definition_service.py` does support file includes with the `_resolve_includes` method, but with additional features not mentioned in the document:
- Maximum include depth of 10
- Circular include detection
- Detailed error messages for include-related issues
