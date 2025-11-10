# Testing Guide

## Test Structure

```
tests/
├── test_server.py    # MCP server and tool tests
├── test_ui.py        # UI component tests
└── test_cli.py       # CLI integration tests
```

## Running Tests

### All Tests
```bash
uv run pytest
```

### Specific Test File
```bash
uv run pytest tests/test_server.py -v
```

### With Coverage
```bash
uv run pytest --cov --cov-report=html
open htmlcov/index.html
```

### Watch Mode
```bash
uv run pytest-watch
```

## Test Categories

### 1. Integration Tests (`test_server.py`)

Test the full MCP protocol flow with minimal mocking:

```python
@pytest.mark.asyncio
async def test_request_text_input_tool(mcp_client: Client) -> None:
    with patch("hitl_mcp_cli.server.prompt_text", new_callable=AsyncMock) as mock:
        mock.return_value = "Test Input"
        result = await mcp_client.call_tool("request_text_input", {...})
        assert result.data == "Test Input"
```

**What we test**:
- MCP protocol initialization
- Tool registration and schemas
- Tool invocation
- Parameter validation
- Error handling

### 2. Unit Tests (`test_ui.py`)

Test UI components in isolation:

```python
def test_show_success() -> None:
    with patch("hitl_mcp_cli.ui.feedback.console") as mock_console:
        show_success("Operation completed")
        assert mock_console.print.called
```

**What we test**:
- Banner display
- Feedback messages
- Component behavior

### 3. CLI Tests (`test_cli.py`)

Test command-line interface:

```python
def test_cli_help() -> None:
    result = subprocess.run([sys.executable, "-m", "hitl_mcp_cli.cli", "--help"], ...)
    assert "--port" in result.stdout
```

**What we test**:
- Argument parsing
- Help messages
- Banner integration

## Writing Tests

### Async Tests

Use `@pytest.mark.asyncio` for async functions:

```python
@pytest.mark.asyncio
async def test_async_function() -> None:
    result = await some_async_function()
    assert result == expected
```

### Mocking

#### Mock Async Functions
```python
from unittest.mock import AsyncMock

with patch("module.async_func", new_callable=AsyncMock) as mock:
    mock.return_value = "result"
    # Test code
```

#### Mock Sync Functions
```python
from unittest.mock import Mock

with patch("module.sync_func") as mock:
    mock.return_value = "result"
    # Test code
```

### Fixtures

Create reusable test fixtures:

```python
@pytest.fixture
async def mcp_client() -> Client:
    async with Client(mcp) as client:
        yield client
```

## Coverage Goals

- **Overall**: > 80%
- **Server**: > 90% (critical business logic)
- **UI**: > 70% (visual components harder to test)
- **CLI**: > 60% (integration tests)

## Testing Best Practices

### 1. Test Behavior, Not Implementation

❌ Bad:
```python
def test_internal_method():
    obj._internal_method()  # Testing private method
```

✅ Good:
```python
def test_public_api():
    result = obj.public_method()
    assert result == expected
```

### 2. Use Descriptive Test Names

❌ Bad:
```python
def test_1():
    ...
```

✅ Good:
```python
def test_request_text_input_returns_user_input():
    ...
```

### 3. Arrange-Act-Assert Pattern

```python
def test_something():
    # Arrange
    setup_data = create_test_data()

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result == expected
```

### 4. One Assertion Per Test (When Possible)

❌ Bad:
```python
def test_everything():
    assert func1() == 1
    assert func2() == 2
    assert func3() == 3
```

✅ Good:
```python
def test_func1():
    assert func1() == 1

def test_func2():
    assert func2() == 2
```

### 5. Test Edge Cases

```python
def test_empty_input():
    assert handle_input("") == default_value

def test_none_input():
    assert handle_input(None) == default_value

def test_very_long_input():
    long_string = "x" * 10000
    assert handle_input(long_string) is not None
```

## Manual Testing

### Interactive Testing

Run the example script:
```bash
uv run python example.py
```

### FastMCP Dev Server

Test tools in web UI:
```bash
fastmcp dev hitl_mcp_cli/server.py
```

Open http://localhost:5173

### MCP Inspector

Test full MCP protocol:
```bash
npx @modelcontextprotocol/inspector hitl-mcp
```

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Release tags

CI checks:
- All tests pass
- Coverage meets thresholds
- Type checking (mypy)
- Linting (ruff, black, isort)

## Debugging Tests

### Run Single Test
```bash
uv run pytest tests/test_server.py::test_specific_test -v
```

### Show Print Statements
```bash
uv run pytest -s
```

### Drop into Debugger on Failure
```bash
uv run pytest --pdb
```

### Show Locals on Failure
```bash
uv run pytest -l
```

## Performance Testing

### Measure Test Duration
```bash
uv run pytest --durations=10
```

### Profile Tests
```bash
uv run pytest --profile
```

## Test Data

Keep test data minimal and focused:

```python
# Good: Minimal test data
test_choices = ["A", "B", "C"]

# Bad: Excessive test data
test_choices = [f"Option {i}" for i in range(1000)]
```

## Mocking Guidelines

### When to Mock

✅ Mock:
- External services
- User input (InquirerPy)
- File system operations
- Network calls
- Time-dependent operations

❌ Don't Mock:
- Simple data structures
- Pure functions
- Your own business logic (test it!)

### Mock Verification

```python
# Verify mock was called
mock.assert_called_once()

# Verify call arguments
mock.assert_called_with(expected_arg)

# Verify call count
assert mock.call_count == 2
```

## Common Issues

### Async Test Not Running

Make sure you have `@pytest.mark.asyncio`:
```python
@pytest.mark.asyncio  # Don't forget this!
async def test_async():
    ...
```

### Mock Not Working

Check the patch path:
```python
# Patch where it's used, not where it's defined
with patch("hitl_mcp_cli.server.prompt_text"):  # ✅
    ...

with patch("hitl_mcp_cli.ui.prompts.prompt_text"):  # ❌
    ...
```

### Fixture Not Found

Make sure fixture is in scope:
```python
# In conftest.py or same file
@pytest.fixture
def my_fixture():
    return "value"

# In test
def test_something(my_fixture):  # Fixture name as parameter
    assert my_fixture == "value"
```
