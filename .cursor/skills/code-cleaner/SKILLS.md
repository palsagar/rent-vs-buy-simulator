---
name: code-cleaner
description: Comprehensively lint, format, and type-check Python code using ruff and ty. Iteratively fixes all linting, formatting, and type issues within a user-defined scope.
---

# Python Lint & Format

Lint, format, and type-check Python code using `ruff` and `ty` to identify and fix issues across files in a specified scope.

## When to Use

- User asks to lint, format, or clean up Python code
- User mentions tools like ruff or type checking
- User requests to "fix all issues" or "clean up" Python files
- Preparing code for pull requests or CI/CD pipelines

## Instructions

### 1. Clarify Scope

Determine:
- **Scope**: Which files or directories to process?
- **Fix Level**: Auto-fix issues or just report them?
- **Type Checking**: Include type checking? (default: yes)
- **Configuration**: Check for existing config files (pyproject.toml, ruff.toml)

If unclear, ask the user before proceeding.

### 2. Discover Scope

Identify Python files in scope:

```bash
find /path/to/scope -name "*.py" -type f
```

Report how many files were found and confirm before proceeding.

### 3. Initial Assessment

Run tools in check-only mode:

```bash
ruff check /path/to/scope
ruff format --check /path/to/scope
ty /path/to/scope
```

Summarize findings: linting issues count, files with formatting issues, type errors count.

### 4. Iterative Fixing Process

#### Step A: Format with Ruff

```bash
ruff format /path/to/scope
```

Report how many files were reformatted.

#### Step B: Auto-fix Linting Issues

```bash
ruff check --fix /path/to/scope
```

#### Step C: Manual Linting Fixes

For remaining issues:
1. Run `ruff check /path/to/scope` to see remaining issues
2. Group by type and file
3. Fix manually; explain complex fixes before applying
4. Re-run `ruff check` after each batch
5. Iterate until resolved or user confirms to skip

#### Step D: Fix Type Issues

1. Run `ty /path/to/scope` to see type errors
2. For each error:
   - **Missing type hints**: Add annotations to functions and variables
   - **Type mismatches**: Fix incorrect types or add casts
   - **Missing imports**: Add typing imports (`from typing import ...`)
   - **Incompatible types**: Refactor to satisfy type constraints
   - **Any types**: Replace `Any` with specific types where possible

3. Common patterns:
   ```python
   def process(data: dict[str, Any]) -> list[str]: ...
   items: list[int] = []
   def get_user(user_id: int) -> Optional[User]: ...
   if isinstance(value, str): ...  # type narrowing
   ```

4. For stubborn errors: add `# type: ignore[error-code]` with explanation, or ask user for guidance
5. Re-run `ty` after each batch
6. Iterate until passing or errors are documented/suppressed

### 5. Configuration

If no config exists, suggest creating `pyproject.toml`:

```toml
[tool.ruff]
line-length = 88  
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]
```

### 6. Edge Cases

- **Third-party code**: Skip vendor directories
- **Generated code**: Add `# ruff: noqa` or type ignore comments
- **Test files**: May need different rules
- **Legacy code**: Consider incremental adoption (one module at a time)
- **Conflicting fixes**: Revert and document if functionality breaks

### 7. Final Verification

```bash
ruff check /path/to/scope
ruff format --check /path/to/scope
ty /path/to/scope
```

### 8. Summary Report

Provide:
- Total files processed
- Issues fixed (formatting, linting, type errors)
- Remaining issues and why not fixed
- Configuration files created/modified

### 9. Best Practices

- Ensure user has committed changes before large fixes
- For 100+ files, offer incremental processing
- Explain complex fixes; don't silently change business logic
- Preserve behavior; ask when uncertain
- Document suppressions with error codes and reasons
- Encourage running tests after fixes

### Common Commands

```bash
ruff check <path>              # Check linting
ruff check --fix <path>        # Auto-fix
ruff format <path>             # Format code
ruff format --check <path>     # Check formatting
ty <path>                      # Type check

# Combined
ruff format . && ruff check --fix . && ty .
```

### Error Handling

- If configuration has syntax errors, fix them first
- If fixes cause test failures, revert and explain
- If Python version incompatible, adjust target-version in config
- For permission errors, suggest appropriate permissions or adjust scope