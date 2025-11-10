# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
