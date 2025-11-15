---
description: Pre-commit review checklist for code changes
---

# Pre-Commit Review Checklist

Comprehensive review checklist to ensure code quality before committing.

## Your Task

Go through this checklist systematically and verify each item:

### 1. Code Quality
- [ ] Run `/lint` command - all checks pass
- [ ] Run `/test` command - all tests pass with ≥95% coverage
- [ ] No commented-out code (unless with explanation)
- [ ] No debug print statements or console.logs
- [ ] No hardcoded values that should be configurable

### 2. Testing
- [ ] All new features have tests
- [ ] All bug fixes have regression tests
- [ ] Tests are meaningful and test actual behavior
- [ ] Tests have descriptive names and docstrings
- [ ] Edge cases are covered
- [ ] Error paths are tested

### 3. Documentation
- [ ] All new functions have Google-style docstrings
- [ ] All parameters have type hints
- [ ] README.md updated for user-facing changes
- [ ] CHANGELOG.md updated with changes
- [ ] Inline comments for complex logic
- [ ] No outdated documentation

### 4. Security
- [ ] No secrets, API keys, or credentials in code
- [ ] User inputs are validated and sanitized
- [ ] No SQL injection vulnerabilities
- [ ] No command injection vulnerabilities
- [ ] Dependencies are up to date and secure
- [ ] `uv run bandit -r hitl_mcp_cli/` passes

### 5. Git Hygiene
- [ ] Only relevant files staged (check `git status`)
- [ ] No build artifacts, logs, or cache files
- [ ] .gitignore is comprehensive
- [ ] Commit message follows conventional commits format
- [ ] Changes are in appropriate branch

### 6. Architecture
- [ ] Code follows project structure
- [ ] Async-first design for I/O operations
- [ ] Proper error handling with try/except
- [ ] No circular dependencies
- [ ] Follows SOLID principles

### 7. Performance
- [ ] No obvious performance issues
- [ ] Async operations use gather() for parallelism
- [ ] No unnecessary loops or iterations
- [ ] Resources are properly cleaned up

### 8. Breaking Changes
- [ ] No breaking changes in minor/patch versions
- [ ] If breaking changes, version is major bump
- [ ] Migration guide provided for breaking changes
- [ ] Deprecation warnings for removed features

## Actions

After going through the checklist:

1. **Show the checklist results**:
   - List items that passed ✅
   - List items that need attention ⚠️
   - List items that failed ❌

2. **For any failures or warnings**:
   - Explain what needs to be fixed
   - Offer to fix automatically
   - Provide guidance for manual fixes

3. **Suggested commit message**:
   - Generate a conventional commit message
   - Include type (feat/fix/docs/etc.)
   - Include brief description
   - Include body if needed

4. **Final confirmation**:
   - Summarize all changes
   - Confirm all checks pass
   - Ask if ready to commit

## Output Format

```
📋 Pre-Commit Review
━━━━━━━━━━━━━━━━━━━

Code Quality: ✅ PASSED
Testing: ✅ PASSED
Documentation: ⚠️ NEEDS ATTENTION
  - CHANGELOG.md not updated
Security: ✅ PASSED
Git Hygiene: ✅ PASSED
Architecture: ✅ PASSED
Performance: ✅ PASSED
Breaking Changes: ✅ NONE

🎯 Action Items:
1. Update CHANGELOG.md with changes

📝 Suggested Commit Message:
feat: add validation for path inputs

- Add regex validation support
- Improve error messages
- Update tests for new functionality

Ready to commit? [Ask user]
```
