# Documentation Guidelines

## General Principles

- Keep documentation focused, actionable, and up-to-date
- Avoid creating transient or temporary summary documents
- Documentation should serve long-term value, not just capture current state

## Documentation Structure

### Core Documentation (Root Level)
- **README.md**: Primary entry point, quick start, key features
- **CHANGELOG.md**: Version history and notable changes
- **LICENSE**: Project license

### Detailed Documentation (docs/ directory)
- Technical specifications
- Architecture details
- Testing guidelines
- Development standards
- API references
- Usage examples

## Anti-Patterns

### Do NOT Create:
- **Transient summary documents** (e.g., IMPROVEMENTS.md, SUMMARY.md)
- **Temporary status files** that duplicate information
- **One-time review documents** that won't be maintained
- **Redundant documentation** that repeats information from other sources

### Instead:
- Update existing documentation (README, CHANGELOG)
- Add to permanent docs/ structure
- Use git commit messages for historical context
- Keep documentation DRY (Don't Repeat Yourself)

## README Best Practices

- Place most important information first
- Use visual elements (ASCII art, diagrams, screenshots)
- Keep it scannable with clear sections
- Include quick start prominently
- Show, don't just tell (examples over descriptions)

## Changelog Best Practices

- Follow Keep a Changelog format
- Group changes by type (Added, Changed, Fixed, etc.)
- Be specific and actionable
- Link to issues/PRs when relevant
