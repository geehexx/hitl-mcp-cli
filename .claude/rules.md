# HITL MCP CLI - Claude Code Rules

This document contains project-specific rules and guidelines for Claude Code when working on the HITL MCP CLI project.

---

## 🎯 Project Overview

**HITL MCP CLI** is a Human-in-the-Loop MCP Server that bridges the gap between AI autonomy and human judgment. It provides interactive tools for AI agents to request human input at critical decision points.

**Technology Stack:**
- Python 3.11+
- FastMCP (MCP protocol implementation)
- InquirerPy (Interactive prompts)
- Rich (Terminal styling)
- pytest (Testing framework)
- uv (Dependency management)

---

## 📋 Core Principles

### 1. Human-in-the-Loop First
- Every feature must enhance the HITL mission
- Tools must be agent-friendly with clear purposes
- User experience is paramount
- Timeout must always be 0 for HITL operations

### 2. Quality Over Speed
- 95%+ test coverage is mandatory
- All code must pass type checking (mypy strict mode)
- All code must pass linting (ruff, black)
- All public functions require docstrings
- Breaking changes require major version bump

### 3. Accessibility
- Keyboard-only navigation required
- Non-color visual cues (icons) required
- Color blindness support mandatory
- Fuzzy search for long lists (>15 items)
- Screen reader compatibility via terminal

---

## 🔧 Coding Standards

### Python Style

```python
# Line length: 110 characters maximum
# String quotes: Double quotes (enforced by black)
# Indentation: 4 spaces (no tabs)

# Type hints: Required for all functions
async def example_function(param: str, count: int = 0) -> dict[str, Any]:
    """Brief description of function.

    Longer description if needed.

    Args:
        param: Description of param
        count: Description of optional parameter with default

    Returns:
        Dictionary containing result data

    Raises:
        ValueError: When param is invalid

    Example:
        >>> await example_function("test", 5)
        {"result": "success"}
    """
    pass
```

### Docstring Requirements

**All public functions must have Google-style docstrings:**
- Brief description (one line)
- Args section (with types)
- Returns section (with types)
- Raises section (if applicable)
- Example section (encouraged)

### Async-First Design

**All new MCP tools must be async:**
```python
# Correct
@mcp.tool()
async def new_tool(param: str) -> str:
    result = await async_operation(param)
    return result

# Incorrect
@mcp.tool()
def new_tool(param: str) -> str:
    return sync_operation(param)
```

**Wrap synchronous code with executor:**
```python
from functools import wraps
import asyncio

def sync_to_async(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: func(*args, **kwargs)
        )
    return wrapper

@sync_to_async
def blocking_function() -> str:
    # Synchronous code here
    return result
```

---

## 🧪 Testing Requirements

### Test Coverage
- **Minimum 95% coverage** for all code
- All new features MUST include tests
- All bug fixes MUST include regression tests
- Test files mirror source structure

### Test Organization
```
tests/
├── test_server.py          # MCP protocol and tool tests
├── test_mcp_integration.py # Integration tests
├── test_edge_cases.py      # Edge cases and boundaries
├── test_prompts.py         # UI prompt tests
├── test_error_handling.py  # Error handling tests
└── test_*.py               # Feature-specific tests
```

### Test Patterns
```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_feature_name(mcp_client):
    """Test description following Google style."""
    # Arrange
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "expected_value"

        # Act
        result = await mcp_client.call_tool("request_text_input", {"prompt": "Test"})

        # Assert
        assert result is not None
        assert not result.is_error
        assert result.data == "expected_value"
        mock.assert_called_once()
```

### Running Tests
```bash
# All tests with coverage
uv run pytest --cov --cov-report=html

# Specific test file
uv run pytest tests/test_server.py -v

# Specific test function
uv run pytest tests/test_server.py::test_function_name -v

# With debug output
uv run pytest -vv -s
```

---

## 🔍 Code Quality Checks

### Before Every Commit

**Run all quality checks:**
```bash
# 1. Tests with coverage
uv run pytest --cov

# 2. Type checking (strict mode)
uv run mypy hitl_mcp_cli/

# 3. Linting
uv run ruff check .

# 4. Code formatting
uv run black .
uv run isort .

# Or use the /lint command to run all at once
```

**All checks MUST pass before committing!**

### Pre-commit Hooks
```bash
# Install hooks (one time)
pre-commit install

# Hooks will run automatically on commit
# Manually run on all files:
pre-commit run --all-files
```

---

## 📦 MCP Server Guidelines

### Tool Design Principles

**1. Clear Purpose**
- Each tool should solve one specific HITL use case
- Tool names must be descriptive and action-oriented
- Parameters must have clear, unambiguous meanings

**2. Type Safety**
- All parameters must have type hints
- Use Literal types for enums
- Validate inputs at the tool boundary

**3. Error Handling**
```python
@mcp.tool()
async def example_tool(param: str) -> str:
    """Tool description."""
    try:
        result = await ui_function(param)
        return result
    except KeyboardInterrupt:
        # User pressed Ctrl+C
        raise Exception("User cancelled the operation") from None
    except Exception as e:
        # Unexpected error
        raise Exception(f"Operation failed: {e}") from e
```

### Current MCP Tools

**Never modify tool signatures without version bump!**

1. `request_text_input` - Collect text with optional validation
2. `request_selection` - Single/multiple choice selection
3. `request_confirmation` - Yes/no approval
4. `request_path_input` - File/directory path collection
5. `notify_completion` - Status notifications

### Testing MCP Tools

```bash
# Development server
fastmcp dev hitl_mcp_cli/server.py

# MCP Inspector (external testing)
npx @modelcontextprotocol/inspector hitl-mcp

# Example script
uv run python example.py
```

---

## 🎨 UI/UX Guidelines

### Accessibility First
- **Icons required** for all prompt types (not just colors)
- **Keyboard navigation** must work for all interactions
- **Long lists** (>15 items) must use fuzzy search
- **Error messages** must be clear and actionable

### Prompt Styling
```python
from hitl_mcp_cli.ui import ICONS

# Use icons for visual cues
icon = ICONS["input"]  # or "select", "confirm", "path", "success", "error"

# Color-coded but not color-dependent
# Icons ensure accessibility for color blindness
```

### Error Messages
**Good:**
```
❌ Validation failed: Path '/invalid' does not exist
   Please provide an existing file path.
```

**Bad:**
```
Error: Invalid input
```

---

## 🔒 Security Guidelines

### Never Commit Secrets
**Forbidden in git:**
- `.env`, `.envrc` files
- `credentials.json`
- API keys, tokens, passwords
- Private keys (`.key`, `.pem`, `.p12`)
- SSH keys

**Use environment variables:**
```python
import os

# Good
api_key = os.getenv("API_KEY")

# Bad
api_key = "sk-1234567890abcdef"
```

### Input Validation
**Always validate and sanitize:**
```python
# Regex validation for text input
validate_pattern=r"^[a-z0-9-]+$"

# Path validation
must_exist=True  # Verify path exists

# Shell command safety
import shlex
safe_arg = shlex.quote(user_input)
```

### Security Scanning
```bash
# Run bandit security scanner
uv run bandit -r hitl_mcp_cli/

# Must pass with no issues
```

---

## 📝 Documentation Standards

### Required Documentation

**For all changes:**
1. Update CHANGELOG.md (Keep a Changelog format)
2. Update README.md for user-facing changes
3. Update relevant docs/ files for architecture changes
4. Add docstrings to all new functions
5. Update examples if tool signatures change

### CHANGELOG Format
```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature description with context

### Changed
- Changed behavior description with migration notes

### Fixed
- Bug fix description with issue reference

### Deprecated
- Deprecated feature description with alternatives

### Security
- Security fix description (if applicable)
```

### Commit Message Format

**Use Conventional Commits:**
```bash
# Format: <type>: <description>

feat: add validation for path inputs
fix: resolve multiline terminal clearing issue
docs: update README with new tool examples
test: add edge case tests for selection tool
refactor: simplify prompt wrapper logic
chore: update dependencies
perf: optimize async executor usage
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `test` - Test additions/changes
- `refactor` - Code refactoring
- `chore` - Maintenance tasks
- `perf` - Performance improvements

---

## 🚀 Release Process

### Version Numbering

**Semantic Versioning (X.Y.Z):**
- **Major (X)**: Breaking changes (tool signature changes, removed features)
- **Minor (Y)**: New features, backwards compatible
- **Patch (Z)**: Bug fixes, no new features

### Release Checklist

**Before release:**
1. ✅ Update version in `pyproject.toml`
2. ✅ Update `CHANGELOG.md` with all changes
3. ✅ Run full test suite: `uv run pytest --cov`
4. ✅ Run all quality checks: `/lint`
5. ✅ Test example script: `uv run python example.py`
6. ✅ Test MCP inspector: `npx @modelcontextprotocol/inspector hitl-mcp`
7. ✅ Build package: `uv build`
8. ✅ Test installation: `uvx hitl-mcp-cli@latest`
9. ✅ Create git tag: `git tag vX.Y.Z`
10. ✅ Push to PyPI: `uv publish`
11. ✅ Create GitHub release with notes

---

## 🔄 Git Workflow

### Branch Strategy
- `main` - Stable releases only
- `claude/*` - Feature branches (auto-created by Claude Code)
- `feature/*` - Manual feature branches
- `fix/*` - Bug fix branches

### Current Branch
**Target:** `claude/initialize-repository-019oCBGz78fZKEyiDbGhLdp1`

### Commit Requirements

**Before committing:**
1. All tests pass
2. All quality checks pass
3. CHANGELOG.md updated
4. No secrets in code
5. Conventional commit message

**Pre-commit hooks enforce:**
- Code formatting (black, isort)
- Linting (ruff)
- Security scanning (bandit)
- Type hints presence

### Pull Request Requirements

**PR must include:**
- Clear description of changes
- Link to related issues
- Test coverage maintained/improved
- Documentation updated
- CHANGELOG.md entry
- Screenshots/examples (if UI changes)
- Breaking changes clearly marked

---

## 🏗️ Architecture Patterns

### Module Organization
```
hitl_mcp_cli/
├── server.py          # MCP server and tool registration
├── cli.py             # Command-line interface
├── __init__.py        # Package initialization
└── ui/
    ├── prompts.py     # Prompt wrappers
    ├── feedback.py    # Visual feedback
    ├── banner.py      # Startup banner
    └── __init__.py    # UI package init
```

### Dependency Injection
```python
# Server imports UI (dependency injection)
from .ui import prompt_text, display_notification

# UI is independent (no server imports)
# This enables easy testing
```

### Adding New Tools

**Process:**
1. Define tool in `server.py` with `@mcp.tool()`
2. Create UI function in `ui/prompts.py`
3. Add tests in `tests/test_server.py`
4. Update README.md with examples
5. Update CHANGELOG.md
6. Increment minor version

---

## 🧩 Deferred Enhancements

**Before adding new features, check `docs/FUTURE.md`!**

This file contains planned enhancements that have been deferred. Check it to:
- Avoid duplicating planned work
- Understand future direction
- Add your ideas for discussion

**Adding to FUTURE.md:**
```markdown
## Category

- **Feature name**: Description
  - Rationale: Why it's useful
  - Complexity: Low/Medium/High
  - Dependencies: What's required
```

---

## ⚡ Performance Guidelines

### Async Best Practices
- Use `asyncio.gather()` for parallel operations
- Avoid blocking calls in async functions
- Use executor for CPU-bound operations
- Cache expensive computations

### Memory Management
- Clean up resources in `finally` blocks
- Avoid circular references
- Use context managers for file operations
- Profile before optimizing

### Benchmarking
```bash
# Profile execution
python -m cProfile -o profile.stats example.py

# Analyze profile
python -m pstats profile.stats
```

---

## 🎓 Learning Resources

### MCP Protocol
- [Model Context Protocol Docs](https://modelcontextprotocol.io)
- [FastMCP Documentation](https://github.com/jlowin/fastmcp)
- [MCP Specification](https://spec.modelcontextprotocol.io)

### Python Best Practices
- [Python Type Hints](https://docs.python.org/3/library/typing.html)
- [Asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
- [pytest Documentation](https://docs.pytest.org)

### Project Docs
- `README.md` - User guide
- `ARCHITECTURE.md` - System design
- `TESTING.md` - Testing guide
- `ACCESSIBILITY.md` - Accessibility features
- `CONTRIBUTING.md` - Contribution guide

---

## 🎯 Quick Reference

### Most Used Commands
```bash
# Testing
uv run pytest --cov              # Run tests with coverage
uv run pytest -k test_name       # Run specific test

# Quality Checks
uv run mypy hitl_mcp_cli/        # Type checking
uv run ruff check .              # Linting
uv run black .                   # Formatting

# Development
fastmcp dev hitl_mcp_cli/server.py    # Dev server
uv run python example.py              # Test example

# Custom Commands (slash commands)
/test      # Run full test suite
/lint      # Run all quality checks
/review    # Pre-commit checklist
/deploy    # Release checklist
```

### Key Files to Update
- `pyproject.toml` - Version, dependencies
- `CHANGELOG.md` - User-facing changes
- `README.md` - User documentation
- `docs/FUTURE.md` - Deferred features

### Contacts
- **Repository**: https://github.com/geehexx/hitl-mcp-cli
- **Issues**: https://github.com/geehexx/hitl-mcp-cli/issues
- **Discussions**: https://github.com/geehexx/hitl-mcp-cli/discussions

---

## ✅ Pre-Flight Checklist

**Before any commit:**
- [ ] Tests pass (`uv run pytest --cov`)
- [ ] Type checking passes (`uv run mypy hitl_mcp_cli/`)
- [ ] Linting passes (`uv run ruff check .`)
- [ ] Formatting applied (`uv run black .`)
- [ ] CHANGELOG.md updated
- [ ] No secrets in code
- [ ] Docstrings added to new functions
- [ ] Conventional commit message prepared

**Before any PR:**
- [ ] All commits follow guidelines
- [ ] PR description is clear
- [ ] Tests cover new code
- [ ] Documentation updated
- [ ] Breaking changes documented
- [ ] Examples tested

**Before any release:**
- [ ] Version bumped appropriately
- [ ] CHANGELOG.md complete
- [ ] All quality checks pass
- [ ] Package builds successfully
- [ ] Installation tested
- [ ] Git tag created
- [ ] Release notes prepared

---

*Last updated: 2025-11-15*
*Project version: 0.4.0*
*Claude Code rules format version: 1.0*
