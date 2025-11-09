# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Custom startup banner with gradient colors and animation
- Emoji icons for all prompt types (text, select, checkbox, confirm, path)
- Visual feedback components (loading indicators, status messages)
- CLI flags: `--no-banner` and `--no-animation` for customization
- Comprehensive UI component tests

### Changed
- Enhanced prompt styling with icons and better visual hierarchy
- Improved notification display with icons and spacing
- Suppressed FastMCP default startup messages for cleaner output
- Better multiline text prompt formatting with Rich panels

### Improved
- Overall user experience with more polished terminal UI
- Visual feedback during operations
- Server startup presentation

## [0.1.0] - Initial Release

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
