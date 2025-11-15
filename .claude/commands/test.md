---
description: Run the full test suite with coverage reporting
---

# Run Full Test Suite

Execute the complete test suite for HITL MCP CLI with coverage reporting and detailed output.

## Your Task

1. **Run pytest with coverage**:
   ```bash
   uv run pytest --cov --cov-report=term-missing --cov-report=html -v
   ```

2. **Analyze the results**:
   - Check if all tests passed
   - Review coverage percentage (must be ≥95%)
   - Identify any missing coverage areas
   - Check for any warnings or deprecations

3. **Report findings**:
   - Total tests run
   - Pass/fail count
   - Overall coverage percentage
   - Files with coverage below 95%
   - Any failed tests with details

4. **If tests fail**:
   - Show the failure details
   - Suggest potential fixes
   - Do NOT automatically fix without asking

5. **If coverage is below 95%**:
   - Identify which files need more tests
   - Show specific lines missing coverage
   - Suggest test cases to add

## Additional Checks

After tests complete successfully:
- Verify no test files were skipped
- Check for flaky tests (run multiple times if suspicious)
- Ensure test isolation (no shared state issues)

## Output Format

Provide a clear summary:
```
✅ Test Results
━━━━━━━━━━━━━━━
Total: X tests
Passed: X
Failed: X
Skipped: X

📊 Coverage: X%
[Coverage details per module]

[Any issues or recommendations]
```
