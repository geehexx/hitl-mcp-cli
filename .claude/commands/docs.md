---
description: Documentation update workflow and guidelines
---

# Documentation Update Workflow

Guide for updating and maintaining project documentation.

## Your Task

Help update documentation following project standards.

### Documentation Files

**User-facing:**
- `README.md` - Main user guide and quick start
- `SECURITY.md` - Security policy and reporting
- `CHANGELOG.md` - Version history and changes

**Developer-facing:**
- `CONTRIBUTING.md` - Contribution guidelines
- `docs/ARCHITECTURE.md` - System design and components
- `docs/TESTING.md` - Testing guide and strategies
- `docs/ACCESSIBILITY.md` - Accessibility features
- `docs/FUTURE.md` - Deferred enhancements

**Project configuration:**
- `.claude/rules.md` - Claude Code project rules
- `pyproject.toml` - Package metadata

### Update Workflow

When updating documentation:

1. **Identify what changed**:
   - New features?
   - Bug fixes?
   - Breaking changes?
   - Performance improvements?
   - Architecture changes?

2. **Update CHANGELOG.md** (always):
   ```markdown
   ## [Unreleased]

   ### Added
   - New feature description

   ### Changed
   - Changed behavior description

   ### Fixed
   - Bug fix description
   ```

3. **Update README.md** (if user-facing):
   - Add new features to features list
   - Update quick start if needed
   - Add examples for new tools
   - Update troubleshooting section

4. **Update ARCHITECTURE.md** (if design changed):
   - Update component diagrams
   - Update data flow descriptions
   - Document new patterns

5. **Update TESTING.md** (if testing changed):
   - Add new test strategies
   - Document new test files
   - Update coverage requirements

6. **Update CONTRIBUTING.md** (if workflow changed):
   - Update setup instructions
   - Add new quality checks
   - Update review process

7. **Update FUTURE.md** (for deferred ideas):
   - Add ideas for future consideration
   - Remove items that were implemented
   - Categorize by complexity

### Documentation Standards

**README.md:**
- Scannable with clear headings
- Code examples that work
- Visual hierarchy with emoji (sparingly)
- Up-to-date feature list
- Working quick start instructions

**Code comments:**
- Google-style docstrings for all public functions
- Type hints for all parameters
- Examples in docstrings
- Why, not what (code shows what)

**CHANGELOG.md:**
- Keep a Changelog format
- Group by category (Added, Changed, Fixed, etc.)
- User-focused language
- Link to issues/PRs
- Release dates in YYYY-MM-DD format

### Verification Steps

After updating documentation:

1. **Test all code examples**:
   ```bash
   # Verify code examples work
   # Copy-paste and run them
   ```

2. **Check for broken links**:
   - Internal links (e.g., [ARCHITECTURE.md])
   - External links (GitHub, PyPI, etc.)

3. **Review formatting**:
   - Markdown renders correctly
   - Code blocks have language specified
   - Tables are properly formatted

4. **Check consistency**:
   - Version numbers match
   - Feature lists match actual features
   - Examples use current API

### Common Updates

**New feature added:**
```markdown
1. README.md - Add to features, add example
2. CHANGELOG.md - Add to [Unreleased] > Added
3. ARCHITECTURE.md - Update if design changed
4. CONTRIBUTING.md - Update if workflow affected
```

**Bug fixed:**
```markdown
1. CHANGELOG.md - Add to [Unreleased] > Fixed
2. README.md - Update troubleshooting if relevant
```

**Breaking change:**
```markdown
1. CHANGELOG.md - Add to [Unreleased] > Changed (with migration)
2. README.md - Update all affected examples
3. ARCHITECTURE.md - Update if design changed
4. Version bump to next major
```

**Security fix:**
```markdown
1. CHANGELOG.md - Add to [Unreleased] > Security
2. SECURITY.md - Update if policy changed
3. Coordinate with maintainers on disclosure
```

### Output Format

After updating documentation:

```
📚 Documentation Updated
━━━━━━━━━━━━━━━━━━━━━

Files Updated:
✅ CHANGELOG.md - Added feature description
✅ README.md - Updated examples
✅ docs/ARCHITECTURE.md - Added new component

Verification:
✅ All code examples tested
✅ No broken links found
✅ Formatting correct
✅ Versions consistent

Summary:
Updated documentation for [feature/change]. All examples
tested and working. Ready to commit.

Suggested commit message:
docs: update documentation for [feature]
```

### Quality Checklist

Before finalizing documentation updates:

- [ ] All code examples tested and working
- [ ] No spelling or grammar errors
- [ ] Consistent terminology throughout
- [ ] Version numbers are correct
- [ ] Links are working
- [ ] Formatting is correct
- [ ] CHANGELOG.md updated
- [ ] User-facing changes in README.md
