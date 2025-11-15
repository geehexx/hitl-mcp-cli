---
description: Run all code quality checks (mypy, ruff, black, isort)
---

# Run All Code Quality Checks

Execute all linting, formatting, and type-checking tools to ensure code quality.

## Your Task

Run the following checks in sequence and report results:

### 1. Type Checking (mypy)
```bash
uv run mypy hitl_mcp_cli/
```
- Must pass with zero errors
- Strict mode is enabled
- Report any type violations

### 2. Linting (ruff)
```bash
uv run ruff check .
```
- Check for code quality issues
- Report any violations
- Suggest fixes if available

### 3. Code Formatting (black)
```bash
uv run black --check .
```
- Verify code is properly formatted
- If not formatted, ask before applying changes
- Show which files need formatting

### 4. Import Sorting (isort)
```bash
uv run isort --check-only .
```
- Verify imports are sorted correctly
- If not sorted, ask before applying changes
- Show which files need sorting

### 5. Security Scanning (bandit)
```bash
uv run bandit -r hitl_mcp_cli/
```
- Scan for security issues
- Report any findings with severity
- Suggest fixes for security issues

## Handling Failures

**If any check fails:**
1. Show the specific errors
2. Explain what's wrong
3. Ask if you should fix it
4. If yes, fix and re-run checks

**For formatting issues:**
```bash
# Fix black formatting
uv run black .

# Fix isort
uv run isort .
```

**For linting issues:**
```bash
# Auto-fix what's possible
uv run ruff check --fix .
```

## Output Format

Provide a comprehensive summary:
```
🔍 Code Quality Report
━━━━━━━━━━━━━━━━━━━━━

✅ mypy: PASSED
✅ ruff: PASSED
✅ black: PASSED
✅ isort: PASSED
✅ bandit: PASSED

All quality checks passed! ✨

[or details of any failures]
```

## Success Criteria

All checks must pass before code can be committed. If any fail, offer to fix them automatically.
