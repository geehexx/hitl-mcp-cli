# Contributing to HITL MCP CLI

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication

## Getting Started

### Prerequisites

- Python 3.11 or higher
- uv (recommended) or pip
- Git

### Development Setup

```bash
# Clone the repository
git clone https://github.com/geehexx/hitl-mcp-cli.git
cd hitl-mcp-cli

# Install dependencies
uv sync --all-extras

# Run tests to verify setup
uv run pytest
```

## Development Workflow

### 1. Create a Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

Follow the coding standards documented in `.amazonq/rules/memory-bank/guidelines.md`:

- **Line length**: 110 characters maximum
- **String quotes**: Double quotes
- **Type hints**: Required for all functions
- **Docstrings**: Google-style with Args/Returns
- **Async-first**: Use async def for all new tools

### 3. Write Tests

All new features must include tests:

```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov

# Run specific test file
uv run pytest tests/test_your_feature.py -v
```

### 4. Check Code Quality

```bash
# Type checking
uv run mypy hitl_mcp_cli/

# Linting
uv run ruff check .

# Code formatting
uv run black .
uv run isort .

# Run all checks
uv run pytest && uv run mypy hitl_mcp_cli/ && uv run ruff check . && uv run black --check . && uv run isort --check .
```

### 5. Update Documentation

- Update README.md if adding user-facing features
- Update CHANGELOG.md following Keep a Changelog format
- Update docs/ if changing architecture or testing
- Add to docs/FUTURE.md if deferring enhancements

### 6. Commit Changes

Use conventional commit messages:

```bash
git commit -m "feat: add new tool for X"
git commit -m "fix: resolve issue with Y"
git commit -m "docs: update README with Z"
git commit -m "test: add tests for W"
git commit -m "refactor: improve V implementation"
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `perf`

### 7. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a Pull Request on GitHub with:
- Clear description of changes
- Link to related issues
- Screenshots/examples if applicable
- Test results

## What to Contribute

### High Priority

- Bug fixes
- Documentation improvements
- Test coverage improvements
- Performance optimizations
- Security enhancements

### Medium Priority

- New validation patterns
- Error message improvements
- Cross-platform compatibility fixes
- Example scripts and tutorials

### Low Priority (Discuss First)

- New tools (must fit HITL mission)
- UI/UX changes (must maintain simplicity)
- New dependencies (must justify necessity)
- Breaking changes (require major version bump)

## Testing Guidelines

### Test Organization

- `tests/test_server.py`: MCP protocol and tool tests
- `tests/test_mcp_integration.py`: Integration tests
- `tests/test_edge_cases.py`: Edge case and boundary tests
- `tests/test_prompts.py`: UI prompt tests
- `tests/test_error_handling.py`: Error handling tests

### Writing Tests

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_your_feature(mcp_client):
    \"\"\"Test description.\"\"\"
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "expected"

        result = await mcp_client.call_tool("request_text_input", {"prompt": "Test"})

        assert result is not None
        assert not result.is_error
        assert result.data == "expected"
```

### Test Coverage Requirements

- Minimum 95% coverage for new code
- All new functions must have tests
- Edge cases must be covered
- Error paths must be tested

## Documentation Standards

### Code Documentation

```python
def function_name(param: str, optional: int = 0) -> bool:
    """Brief description.

    Longer description if needed.

    Args:
        param: Description of param
        optional: Description of optional param

    Returns:
        Description of return value

    Example:
        >>> function_name("test", 5)
        True
    """
```

### README Updates

- Keep it scannable with clear sections
- Use examples over descriptions
- Update table of contents if adding sections
- Test all code examples

### CHANGELOG Updates

Follow Keep a Changelog format:

```markdown
## [Version] - YYYY-MM-DD

### Added
- New feature description

### Changed
- Changed behavior description

### Fixed
- Bug fix description

### Deprecated
- Deprecated feature description
```

## Architecture Decisions

### When to Add a New Tool

New tools must:
1. Solve a real HITL use case
2. Be agent-friendly (clear purpose, simple parameters)
3. Not duplicate existing functionality
4. Maintain async-first design
5. Include comprehensive tests and documentation

### When to Add a Dependency

New dependencies must:
1. Solve a problem that can't be solved with existing deps
2. Be actively maintained
3. Have permissive license (Apache 2.0, MIT, BSD)
4. Not significantly increase package size
5. Be justified in PR description

### When to Make Breaking Changes

Breaking changes require:
1. Major version bump (1.x.x → 2.0.0)
2. Deprecation warnings in previous version
3. Migration guide in CHANGELOG
4. Discussion in GitHub issue first

## Review Process

### Pull Request Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] CHANGELOG updated
- [ ] No new linter warnings
- [ ] Type hints added
- [ ] Commit messages follow convention

### Review Criteria

Reviewers will check:
1. **Correctness**: Does it work as intended?
2. **Tests**: Are there adequate tests?
3. **Documentation**: Is it well-documented?
4. **Style**: Does it follow guidelines?
5. **Simplicity**: Is it the simplest solution?
6. **Performance**: Are there performance concerns?
7. **Security**: Are there security implications?

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue with reproduction steps
- **Features**: Open a GitHub Issue for discussion first
- **Security**: Email maintainers privately

## Recognition

Contributors will be:
- Listed in CHANGELOG for their contributions
- Mentioned in release notes
- Added to GitHub contributors list

Thank you for contributing to HITL MCP CLI!
