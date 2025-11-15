#!/usr/bin/env bash
# UserPromptSubmit Hook for HITL MCP CLI
# This hook runs when the user submits a prompt
# It adds context, validates operations, and provides quality reminders

set -euo pipefail
trap 'exit 0' ERR  # Never block prompts, even on errors

# Get the user's prompt from the hook input (with validation)
PROMPT="${HOOK_INPUT_PROMPT:-}"
CONVERSATION_CONTEXT="${HOOK_INPUT_CONVERSATION:-}"

# Exit gracefully if prompt is empty
if [ -z "$PROMPT" ]; then
    exit 0
fi

# ==============================================================================
# Context Injection Based on Keywords
# ==============================================================================

ADDITIONAL_CONTEXT=""

# Check for testing-related prompts
if echo "$PROMPT" | grep -qiE '(test|pytest|coverage|unit test)'; then
    ADDITIONAL_CONTEXT+="
=== TESTING CONTEXT ===

Test Requirements:
  • All new features MUST include tests
  • Maintain 95%+ test coverage
  • Use pytest with async support
  • Mock external dependencies
  • Test edge cases and error paths

Test Structure:
  • tests/test_server.py - MCP protocol tests
  • tests/test_mcp_integration.py - Integration tests
  • tests/test_edge_cases.py - Edge cases
  • tests/test_prompts.py - UI tests
  • tests/test_error_handling.py - Error handling

Run tests: uv run pytest --cov
"
fi

# Check for MCP-related prompts
if echo "$PROMPT" | grep -qiE '(mcp|tool|server|fastmcp)'; then
    ADDITIONAL_CONTEXT+="
=== MCP SERVER CONTEXT ===

This project IS an MCP server. Key points:
  • Use FastMCP framework (version 2.13.0+)
  • All tools must be async
  • Tools registered with @mcp.tool() decorator
  • Schema generation is automatic
  • Test with: fastmcp dev hitl_mcp_cli/server.py

Available MCP Tools:
  1. request_text_input - Text collection with validation
  2. request_selection - Single/multiple choice
  3. request_confirmation - Yes/no approval
  4. request_path_input - File/directory paths
  5. notify_completion - Status notifications

MCP Client Configuration:
  • Transport: streamable-http
  • Endpoint: http://127.0.0.1:5555/mcp
  • CRITICAL: timeout must be 0 (infinite) for HITL tools
"
fi

# Check for UI-related prompts
if echo "$PROMPT" | grep -qiE '(ui|prompt|inquirer|rich|terminal)'; then
    ADDITIONAL_CONTEXT+="
=== UI/UX CONTEXT ===

UI Stack:
  • InquirerPy - Interactive prompts
  • Rich - Terminal styling
  • Asyncio - Async I/O handling

Accessibility Requirements:
  • Keyboard-only navigation
  • Non-color visual cues (icons)
  • Color blindness support
  • Fuzzy search for long lists (>15 items)
  • Screen reader compatibility

UI Components:
  • ui/prompts.py - Prompt wrappers
  • ui/feedback.py - Visual feedback
  • ui/banner.py - Startup banner

Style Guidelines:
  • Use icons for prompt types
  • Color-coded status messages
  • Smooth animations (can be disabled)
  • Clear error messages
"
fi

# Check for security-related prompts
if echo "$PROMPT" | grep -qiE '(security|secret|credential|password|api key|token)'; then
    ADDITIONAL_CONTEXT+="
=== SECURITY CONTEXT ===

Security Requirements:
  • NEVER commit secrets to git
  • Use environment variables for credentials
  • Validate all user inputs
  • Escape shell variables properly
  • Run security scans with bandit
  • Check SECURITY.md for disclosure policy

Files to Exclude from Git:
  • .env, .envrc
  • credentials.json
  • *.key, *.pem
  • config.local.*

Security Tools:
  • bandit - Python security scanner
  • pre-commit hooks - Automated checks
  • .gitignore - Prevent accidental commits

Command: uv run bandit -r hitl_mcp_cli/
"
fi

# Check for deployment/release prompts
if echo "$PROMPT" | grep -qiE '(deploy|release|publish|version|pypi)'; then
    ADDITIONAL_CONTEXT+="
=== DEPLOYMENT CONTEXT ===

Release Checklist:
  1. Update version in pyproject.toml
  2. Update CHANGELOG.md with all changes
  3. Run full test suite (uv run pytest --cov)
  4. Run all quality checks (/lint command)
  5. Build package (uv build)
  6. Test installation (uvx hitl-mcp-cli@latest)
  7. Create git tag (vX.Y.Z)
  8. Push to PyPI (uv publish)
  9. Create GitHub release with notes

Version Format: Semantic Versioning (X.Y.Z)
  • Major (X): Breaking changes
  • Minor (Y): New features, backwards compatible
  • Patch (Z): Bug fixes

Current Version: 0.4.0
"
fi

# Check for documentation prompts
if echo "$PROMPT" | grep -qiE '(document|readme|docs|comment|docstring)'; then
    ADDITIONAL_CONTEXT+="
=== DOCUMENTATION CONTEXT ===

Documentation Standards:
  • Google-style docstrings required
  • Type hints for all functions
  • README.md - User-facing documentation
  • ARCHITECTURE.md - System design
  • CONTRIBUTING.md - Developer guidelines
  • TESTING.md - Testing guide
  • ACCESSIBILITY.md - Accessibility features
  • FUTURE.md - Deferred enhancements

Docstring Format:
  \"\"\"Brief description.

  Longer description if needed.

  Args:
      param: Description of param
      optional: Description of optional param

  Returns:
      Description of return value

  Example:
      >>> function_name(\"test\", 5)
      True
  \"\"\"

Update CHANGELOG.md for all user-visible changes!
"
fi

# Check for git/commit prompts
if echo "$PROMPT" | grep -qiE '(commit|git|push|pr|pull request)'; then
    ADDITIONAL_CONTEXT+="
=== GIT WORKFLOW CONTEXT ===

Branch: $(git branch --show-current 2>/dev/null || echo 'unknown')

Commit Message Format (Conventional Commits):
  • feat: Add new feature
  • fix: Bug fix
  • docs: Documentation changes
  • test: Test additions/changes
  • refactor: Code refactoring
  • chore: Maintenance tasks
  • perf: Performance improvements

Example:
  git commit -m \"feat: add validation for path inputs\"

Before Committing:
  1. Run tests (uv run pytest)
  2. Run linters (uv run ruff check .)
  3. Format code (uv run black .)
  4. Update CHANGELOG.md
  5. Check for secrets (git diff)

Pre-commit hooks will run automatically if installed.

Target Branch: claude/initialize-repository-019oCBGz78fZKEyiDbGhLdp1
"
fi

# Check for code quality prompts
if echo "$PROMPT" | grep -qiE '(lint|format|quality|style|mypy|black|ruff)'; then
    ADDITIONAL_CONTEXT+="
=== CODE QUALITY CONTEXT ===

Quality Tools Configuration:
  • black: Line length 110, target py311
  • ruff: Line length 110, target py311
  • mypy: Strict mode enabled
  • isort: Black-compatible profile
  • pytest: 95%+ coverage required

Commands:
  uv run mypy hitl_mcp_cli/        # Type checking
  uv run ruff check .              # Linting
  uv run black .                   # Formatting
  uv run isort .                   # Import sorting
  uv run pytest --cov              # Tests with coverage

All checks must pass before committing!

Use /lint command to run all checks at once.
"
fi

# Check for performance-related prompts
if echo "$PROMPT" | grep -qiE '(performance|speed|optimize|async|slow)'; then
    ADDITIONAL_CONTEXT+="
=== PERFORMANCE CONTEXT ===

Performance Guidelines:
  • Use async/await for all I/O operations
  • Minimize blocking calls
  • Use asyncio.gather for parallel operations
  • Cache expensive computations
  • Profile before optimizing

Async Patterns:
  • All MCP tools must be async
  • Use @sync_to_async for blocking code
  • InquirerPy is sync, wrapped with executor
  • FastMCP handles async transparently

Performance Testing:
  • Measure tool response times
  • Check for memory leaks
  • Test with concurrent requests
  • Profile with cProfile if needed
"
fi

# ==============================================================================
# Quality Reminders
# ==============================================================================

# Check if prompt suggests skipping tests
if echo "$PROMPT" | grep -qiE '(skip test|no test|without test|don'\''t test)'; then
    ADDITIONAL_CONTEXT+="
⚠️ WARNING: Testing is mandatory for all code changes!

  • All new features MUST include tests
  • All bug fixes MUST include regression tests
  • Test coverage must remain above 95%
  • Tests ensure reliability and prevent regressions

Please ensure tests are included with your changes.
"
fi

# Check if prompt suggests committing without checks
if echo "$PROMPT" | grep -qiE '(quick commit|skip check|no lint|bypass)'; then
    ADDITIONAL_CONTEXT+="
⚠️ WARNING: Quality checks are essential!

  Before committing, always run:
  1. uv run pytest --cov        (tests)
  2. uv run mypy hitl_mcp_cli/  (type checking)
  3. uv run ruff check .        (linting)
  4. uv run black --check .     (formatting)

  Use /lint command to run all checks.
  Pre-commit hooks will enforce these automatically.
"
fi

# ==============================================================================
# Output Additional Context
# ==============================================================================

if [ -n "$ADDITIONAL_CONTEXT" ]; then
    echo "$ADDITIONAL_CONTEXT"
fi

# Return success (don't block the prompt)
exit 0
