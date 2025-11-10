# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
