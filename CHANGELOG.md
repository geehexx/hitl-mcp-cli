# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.9.0] - 2026-03-26

### Added
- **Session tracking**: All tools now accept `agent_name` and `project_id` params for TUI session display
- **Step indicators**: All tools accept `step` and `total_steps` params; shown as "Step X/Y" in TUI screens
- **Queue history**: Queue panel now shows full history with color-coded status (PENDING/DONE/CANCELLED/MINIMIZED)
- **Clickable queue**: Click any queue row to restore pending/minimized requests or view answered request summaries
- **Session coloring**: Sessions panel color-codes by recency (active <10min = bright, idle = normal, inactive = dim)
- **Collapsible messages**: Messages >200 chars use Textual Collapsible widget (collapsed by default, click to expand)
- **Expand/Collapse All**: ctrl+e toggles all collapsible messages in the current screen
- **Context param**: `hitl_collect` and `hitl_choose` now accept `context` param (was only on `hitl_confirm`)
- **Input validation**: `hitl_collect` now accepts `strip_whitespace`, `required`, and `path_type` params
- **Path normalization**: `hitl_collect` with `input_type='path'` now normalizes `~` and `..` via `Path.expanduser().resolve()`
- **poe tasks**: Replaced Makefile with poethepoet tasks (`uv run poe test`, `uv run poe check`, etc.)
- **Snapshot tests**: Added pytest-textual-snapshot for SVG-based TUI visual regression testing
- **Pilot tests**: Added 23 Textual Pilot tests covering all screen types and interactions

### Changed
- **TUI is now the only mode**: Removed `--no-tui` flag and InquirerPy headless mode
- **Session IDs**: Now uses MCP session ID (not thread ID) for session tracking
- **Textual**: Moved from optional `[tui]` extra to required dependency
- **Formatting**: Replaced black + isort with `ruff format`

### Removed
- `--no-tui` CLI flag and headless InquirerPy mode
- `hitl_mcp_cli/ui/` module (InquirerPy prompts, feedback, banner)
- `hitl_mcp_cli/tui/tmux_manager.py` (unused)
- `Makefile` (replaced by poe tasks)
- `docs/FUTURE.md` (replaced by `docs/ROADMAP.md`)
- `inquirerpy` dependency

## [0.8.0] - 2026-03-22

### Changed
- TUI mode is now the default (previously required `--tui` flag)
- Added `--no-tui` flag for headless/CI environments (env: `HITL_NO_TUI=1`)
- `--tui` flag kept as no-op for backward compatibility

## [0.7.0] - 2026-03-22

### Added
- `--tui` flag for unified Textual TUI mode
- HITLQueue (asyncio.PriorityQueue) for concurrent HITL serialization
- TmuxManager for automatic server lifecycle management (`--tmux` flag)
- Split-pane layout (output stream + HITL queue)
- `hitl_notify` as agent output streaming channel in TUI mode

### Fixed
- ClosedResourceError crash (correct except* placement inside run_stateless_server)

### Security
- Drain pending futures on TUI exit
- Sanitize choices list

## [0.6.0] - 2026-03-22

### Fixed
- HTTP connection timeout crash (mcp-sdk 1.21.0 bug #823 monkey-patch)
- Single-line input overwrites question text (emoji wcwidth via Rich rendering)
- Default text now shown as hint, not pre-filled buffer
- Wrapping/blank line display issues
- Off-by-one spacing in prompts

### Added
- `hitl_ask` alias for `hitl_collect`
- `hitl_confirm` gains `context`, `timeout_seconds`, `timed_out` parameters
- Interaction logging to `~/.local/state/hitl-mcp/interactions.jsonl`
- `notes` parameter on all tools
- Multi-choice escape hatch (free-text when all/none selected)

### Removed
- `hitl_approve_workflow` (merged into `hitl_confirm` severity=high)

### Security
- Rich markup escape on all user-controlled display strings

## [0.5.0] - 2026-03-22

### Changed
- Renamed tools to `hitl_*` taxonomy: `hitl_collect`, `hitl_choose`, `hitl_confirm`, `hitl_notify`
- Merged `request_text_input` and `request_path_input` into `hitl_collect` (use `input_type` param)
- Added `severity` parameter to `hitl_confirm` (low/medium/high)
- Added `options` dict format to `hitl_choose` for rich option descriptions
- Selection prompts automatically enable fuzzy filtering when choices exceed 15 items
- Better UX for long choice lists with search and height constraints

### Added
- Fuzzy search for long choice lists (>15 items) in select/checkbox prompts
- Comprehensive accessibility documentation (docs/ACCESSIBILITY.md)
- Accessibility section in README with feature highlights
- Color blindness compatibility verification and documentation
- `max_height="70%"` for select/checkbox prompts to prevent overwhelming display

### Removed
- Plugin framework references from README and roadmap

### Fixed
- Enable `stateless_http=True` for streamable-http transport (fixes ClientDisconnect errors with Kiro CLI and other stateless MCP clients)

## [0.4.0] - 2025-01-10

### Added
- **NEW**: Meta-development awareness documentation (memory-bank/meta-development.md)
- **NEW**: Comprehensive timeout and error handling tests (test_timeout_handling.py)
- **NEW**: Multiline terminal behavior tests (test_multiline_terminal.py)
- **NEW**: Error handling best practices in README troubleshooting section
- **NEW**: Enhanced server instructions with improved tool discoverability guidance
- **NEW**: Session continuity benefits documentation in server instructions
- **NEW**: Timing triggers and usage categories for tool invocation

### Changed
- **IMPROVED**: Server instructions now emphasize using tools liberally for ANY uncertainty
- **IMPROVED**: Tool discoverability with clear timing triggers and selection logic
- **IMPROVED**: Documentation clarifies when to invoke tools (immediately, not deferred)
- **IMPROVED**: Error handling guidance distinguishes between user cancellation, timeouts, and unexpected errors

### Fixed
- **CRITICAL**: Multiline text input no longer clears terminal after Esc+Enter submission
- **CRITICAL**: Added explicit keybindings for multiline input to prevent screen clearing
- **IMPROVED**: Error handling now properly handles timeout and connection errors (not just KeyboardInterrupt)
- **IMPROVED**: Test coverage for timeout scenarios and error recovery

### Documentation
- Added troubleshooting section for multiline terminal clearing issue
- Added error handling best practices for AI agent developers
- Added connection error troubleshooting guidance
- Clarified error categories (user cancellation, timeout/connection, validation, unexpected)
- Added meta-development context to prevent confusion between development and production usage
- **NEW**: Added Plugin Framework section referencing mcp-plugin-server repository
- **NEW**: Cleaned up docs/FUTURE.md - moved plugin architecture details to dedicated mcp-plugin-server repo
- **NEW**: Added HITL-specific plugin enhancement ideas in FUTURE.md

### Testing
- Added 15+ new tests for timeout handling and error scenarios
- Added 5+ new tests for multiline terminal behavior
- Improved test coverage for concurrent operations and error recovery
- Added tests for long-running operations and sequential tool calls

## [0.3.0] - 2025-01-10

### Added
- **CRITICAL**: Comprehensive timeout documentation and configuration
- **NEW**: Environment variable support (HITL_HOST, HITL_PORT, HITL_LOG_LEVEL, HITL_NO_BANNER)
- **NEW**: CONTRIBUTING.md with comprehensive contribution guidelines
- **NEW**: docs/FUTURE.md for tracking enhancement ideas and non-goals
- **NEW**: Troubleshooting section in README with common issues and solutions
- **NEW**: Security considerations documentation in FUTURE.md
- **NEW**: MCP best practices compliance section in FUTURE.md
- **NEW**: 38 new integration and edge case tests (test_mcp_integration.py, test_edge_cases.py)
- Regex validation best practices in tool docstrings
- Prominent timeout warning at top of README
- Security best practices for users and deployments
- Structured logging with configurable log levels
- Enhanced CLI help with environment variable documentation

### Changed
- **BREAKING**: Updated mcp-config.example.json to use streamable-http transport and timeout=0
- README restructured with "Critical Configuration" section at top
- Enhanced tool documentation with security and validation guidance
- Improved test organization with dedicated integration test suite
- CLI now supports environment variable configuration
- Logging includes debug and info levels for troubleshooting

### Fixed
- **CRITICAL**: Documented MCP client timeout issue (60-second default causes tool failures)
- **CRITICAL**: Verbose uvicorn INFO logs now suppressed by default (only shown in DEBUG mode)
- **CRITICAL**: Access logs only shown when HITL_LOG_LEVEL=DEBUG
- Test assertions using correct attribute name (is_error not isError)
- Error handling tests now properly use raise_on_error=False parameter
- Uvicorn log level now properly matches HITL_LOG_LEVEL setting

### Removed
- IMPROVEMENTS.md (transient document, content moved to FUTURE.md per documentation guidelines)

### Improved
- **Test coverage: 98% → 98%** (100 tests total, up from 81)
- Documentation completeness and clarity
- MCP protocol compliance verification
- Edge case handling (empty inputs, Unicode, very long inputs, special characters)
- Error message clarity in test assertions
- Production readiness with configuration management
- Observability with structured logging

## [0.2.0] - 2025-01-10

### Added
- Custom startup banner with gradient colors and fade-in animation
- Emoji icons for all prompt types (✏️ text, 🎯 select, ☑️ checkbox, ❓ confirm, 📁 path)
- Visual feedback components (loading indicators, status messages)
- CLI flags: `--no-banner` and `--no-animation` for customization
- Comprehensive documentation in docs/ directory (ARCHITECTURE.md, TESTING.md)
- 35 new tests across 3 test files (prompts, feedback, error handling)
- Documentation guidelines in memory bank

### Changed
- **README restructured** with "Why HITL" section at top
- Enhanced tool docstrings with examples and use cases
- Improved prompt styling with icons and better visual hierarchy
- Improved notification display with icons and spacing
- Suppressed FastMCP default banner using `show_banner=False` parameter
- Better multiline text prompt formatting with Rich panels
- Simplified banner animation to prevent duplicate output

### Fixed
- Banner printing multiple times during animation
- FastMCP default banner showing despite custom banner
- Stdout redirection issues in CLI

### Improved
- Overall user experience with more polished terminal UI
- Visual feedback during operations
- Server startup presentation
- **Test coverage: 60% → 99%** (668 statements, 5 missing)
- Documentation quality and organization
- Tool descriptions to be more encouraging and informative

## [0.2.0] - 2025-01-10

Major UX and documentation overhaul with comprehensive testing improvements.

## [0.1.0] - 2025-01-09

### Added
- FastMCP server with 5 interactive tools
- request_text_input: Text input with validation
- request_selection: Single/multiple choice selection
- request_confirmation: Yes/no confirmation
- request_path_input: File/directory path input
- notify_completion: Styled notifications
- InquirerPy integration for prompts
- Rich formatting for terminal output
- Comprehensive test suite
- Full type hints throughout codebase
