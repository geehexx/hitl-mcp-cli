#!/usr/bin/env bash
# SessionStart Hook for HITL MCP CLI
# This hook runs when Claude Code starts or resumes a session
# It sets up the development environment and loads essential context

set -euo pipefail

# Color codes for output (disabled if NO_COLOR is set)
if [ -n "${NO_COLOR:-}" ]; then
    GREEN=''
    YELLOW=''
    RED=''
    BLUE=''
    NC=''
else
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

echo "🚀 Initializing HITL MCP CLI Development Environment..."
echo ""

# ==============================================================================
# 1. Environment Setup
# ==============================================================================

# Get the project directory
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
cd "$PROJECT_DIR"

# Set up environment variables file (avoid duplicates)
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    # Create temp file
    TEMP_ENV=$(mktemp)

    # Copy existing, excluding our variables
    if [ -f "$CLAUDE_ENV_FILE" ]; then
        grep -v "^export PROJECT_ROOT=" "$CLAUDE_ENV_FILE" 2>/dev/null | \
        grep -v "^export PYTHONPATH=" > "$TEMP_ENV" || true
    fi

    # Add our variables
    echo "export PROJECT_ROOT=\"$PROJECT_DIR\"" >> "$TEMP_ENV"
    echo "export PYTHONPATH=\"$PROJECT_DIR:\$PYTHONPATH\"" >> "$TEMP_ENV"

    # Atomic replace
    mv "$TEMP_ENV" "$CLAUDE_ENV_FILE"
fi

# ==============================================================================
# 2. Python Environment Check
# ==============================================================================

echo -e "${BLUE}📦 Checking Python environment...${NC}"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${RED}[WARNING] ⚠️  'uv' is not installed${NC}"
    echo "   → Fix: curl -LsSf https://astral.sh/uv/install.sh | sh"
else
    UV_VERSION=$(uv --version)
    echo "   ✓ uv installed: $UV_VERSION"

    # Check if dependencies need to be synced
    if [ ! -d ".venv" ] || [ "uv.lock" -nt ".venv" ]; then
        echo -e "${YELLOW}   📥 Dependencies out of sync. Running 'uv sync --all-extras'...${NC}"
        if uv sync --all-extras 2>&1 | grep -v "^Audited"; then
            echo -e "${GREEN}   ✓ Dependencies synchronized${NC}"
        fi
    else
        echo "   ✓ Dependencies are up to date"
    fi
fi

# Check Python version
if [ -f ".venv/bin/python" ]; then
    PYTHON_VERSION=$(.venv/bin/python --version)
    echo "   ✓ $PYTHON_VERSION"
else
    echo -e "${YELLOW}   ⚠️  Virtual environment not found${NC}"
fi

echo ""

# ==============================================================================
# 3. Git Status & Context
# ==============================================================================

echo -e "${BLUE}📊 Loading Git context...${NC}"

# Current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")
echo "   Branch: $CURRENT_BRANCH"

# Check if on feature branch
if [[ "$CURRENT_BRANCH" == claude/* ]]; then
    echo -e "${GREEN}   ✓ On Claude feature branch${NC}"
fi

# Git status summary
MODIFIED_FILES=$(git status --porcelain 2>/dev/null | grep "^ M" | wc -l | tr -d ' ')
UNTRACKED_FILES=$(git status --porcelain 2>/dev/null | grep "^??" | wc -l | tr -d ' ')
STAGED_FILES=$(git status --porcelain 2>/dev/null | grep "^M" | wc -l | tr -d ' ')

echo "   Status: $MODIFIED_FILES modified, $STAGED_FILES staged, $UNTRACKED_FILES untracked"

# Recent commits
echo ""
echo "   Recent commits:"
git log --oneline -3 2>/dev/null | sed 's/^/     /'

echo ""

# ==============================================================================
# 4. Test Status Check
# ==============================================================================

echo -e "${BLUE}🧪 Checking test status...${NC}"

if [ -f ".venv/bin/pytest" ]; then
    # Run a quick test to check if any tests are failing
    # Use --collect-only to avoid running tests, just check if they can be collected
    if .venv/bin/pytest --collect-only -q 2>&1 | head -5 | grep -q "error"; then
        echo -e "${RED}   ⚠️  Test collection has errors${NC}"
    else
        TEST_COUNT=$(.venv/bin/pytest --collect-only -q 2>&1 | tail -1 | grep -oP '\d+(?= test)' || echo "0")
        echo -e "${GREEN}   ✓ $TEST_COUNT tests available${NC}"
    fi
else
    echo "   ℹ️  pytest not found in virtual environment"
fi

echo ""

# ==============================================================================
# 5. Pre-commit Hooks Status
# ==============================================================================

echo -e "${BLUE}🔍 Checking pre-commit hooks...${NC}"

if [ -f ".pre-commit-config.yaml" ]; then
    if [ -d ".git/hooks" ] && [ -f ".git/hooks/pre-commit" ]; then
        echo -e "${GREEN}   ✓ Pre-commit hooks installed${NC}"
    else
        echo -e "${YELLOW}   ⚠️  Pre-commit hooks not installed${NC}"
        echo "   Run: pre-commit install"
    fi
else
    echo "   ℹ️  No pre-commit configuration found"
fi

echo ""

# ==============================================================================
# 6. Load Project Context
# ==============================================================================

echo -e "${BLUE}📚 Loading project context...${NC}"
echo ""

# Display project structure
echo "=== PROJECT STRUCTURE ==="
echo ""
echo "HITL MCP CLI - Human-in-the-Loop MCP Server"
echo "Version: 0.4.0"
echo "Python: 3.11+"
echo ""
echo "Key directories:"
echo "  • hitl_mcp_cli/     - Main source code"
echo "  • hitl_mcp_cli/ui/  - User interface components"
echo "  • tests/            - Test suite"
echo "  • docs/             - Documentation"
echo "  • .claude/          - Claude Code configuration"
echo ""

# Load key documentation
if [ -f "README.md" ]; then
    echo "=== PROJECT OVERVIEW ==="
    echo ""
    head -30 README.md | tail -15
    echo ""
fi

if [ -f "CONTRIBUTING.md" ]; then
    echo "=== DEVELOPMENT GUIDELINES ==="
    echo ""
    echo "Coding Standards:"
    echo "  • Line length: 110 characters maximum"
    echo "  • String quotes: Double quotes"
    echo "  • Type hints: Required for all functions"
    echo "  • Docstrings: Google-style with Args/Returns"
    echo "  • Async-first: Use async def for all new tools"
    echo ""
fi

# Check for deferred tasks
if [ -f "docs/FUTURE.md" ]; then
    DEFERRED_COUNT=$(grep -c "^-" docs/FUTURE.md 2>/dev/null || echo "0")
    echo "=== DEFERRED ENHANCEMENTS ==="
    echo ""
    echo "There are $DEFERRED_COUNT deferred tasks in docs/FUTURE.md"
    echo "Review before adding new features to avoid duplication."
    echo ""
fi

# ==============================================================================
# 7. Security & Quality Reminders
# ==============================================================================

echo "=== SECURITY & QUALITY REMINDERS ==="
echo ""
echo "✓ Never commit secrets or credentials"
echo "✓ Run tests before committing (pytest)"
echo "✓ Check types with mypy"
echo "✓ Format with black and ruff"
echo "✓ Maintain 95%+ test coverage"
echo "✓ Update CHANGELOG.md for all changes"
echo "✓ Follow conventional commit messages"
echo ""

# ==============================================================================
# 8. MCP Server Specifics
# ==============================================================================

echo "=== MCP SERVER CONTEXT ==="
echo ""
echo "This project IS an MCP server for human-in-the-loop interactions."
echo ""
echo "Available Tools:"
echo "  1. request_text_input     - Collect text from users"
echo "  2. request_selection      - Present choices (single/multiple)"
echo "  3. request_confirmation   - Get yes/no approval"
echo "  4. request_path_input     - Get file/directory paths"
echo "  5. notify_completion      - Display status notifications"
echo ""
echo "Testing: Use 'fastmcp dev hitl_mcp_cli/server.py' for development"
echo "Running: Use 'hitl-mcp' command to start the server"
echo ""

# ==============================================================================
# 9. Quick Reference Commands
# ==============================================================================

echo "=== QUICK REFERENCE ==="
echo ""
echo "Testing:"
echo "  uv run pytest              # Run all tests"
echo "  uv run pytest --cov        # With coverage"
echo ""
echo "Quality Checks:"
echo "  uv run mypy hitl_mcp_cli/  # Type checking"
echo "  uv run ruff check .        # Linting"
echo "  uv run black .             # Formatting"
echo ""
echo "Development:"
echo "  fastmcp dev hitl_mcp_cli/server.py  # Dev server"
echo "  uv run python example.py            # Test example"
echo ""
echo "Custom Commands:"
echo "  /test      # Run full test suite with coverage"
echo "  /lint      # Run all linters and formatters"
echo "  /review    # Pre-commit review checklist"
echo "  /deploy    # Deployment preparation checklist"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✓ Environment initialized successfully!${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
