---
description: Deployment preparation and release checklist
---

# Deployment Preparation Checklist

Comprehensive checklist for preparing and deploying a new release of HITL MCP CLI.

## Your Task

Guide through the complete release process step by step:

### Phase 1: Pre-Release Validation

1. **Version Check**:
   - [ ] Current version in `pyproject.toml`
   - [ ] Determine new version (major.minor.patch)
   - [ ] Verify semantic versioning rules followed

2. **Quality Assurance**:
   - [ ] Run `/test` - all tests pass
   - [ ] Run `/lint` - all checks pass
   - [ ] Run `/review` - all items satisfied
   - [ ] Manual testing completed
   - [ ] Example script works: `uv run python example.py`

3. **Documentation Review**:
   - [ ] CHANGELOG.md is complete and accurate
   - [ ] README.md reflects current features
   - [ ] All docs/ files are up to date
   - [ ] Breaking changes are documented
   - [ ] Migration guide provided (if needed)

### Phase 2: Build Preparation

4. **Update Version**:
   ```bash
   # Update version in pyproject.toml
   # Format: X.Y.Z
   ```
   - Ask user for new version number
   - Update `pyproject.toml`
   - Update version references in docs

5. **Update CHANGELOG**:
   - Add release date to version header
   - Ensure all changes are documented
   - Group by: Added, Changed, Fixed, Deprecated, Removed, Security

6. **Commit Release Changes**:
   ```bash
   git add pyproject.toml CHANGELOG.md
   git commit -m "chore: prepare release vX.Y.Z"
   ```

### Phase 3: Build & Test

7. **Build Package**:
   ```bash
   uv build
   ```
   - Verify build completes successfully
   - Check dist/ directory created
   - Verify wheel and source dist created

8. **Test Installation**:
   ```bash
   # Test in clean environment
   uvx hitl-mcp-cli@latest
   ```
   - Verify package installs
   - Verify command works
   - Test basic functionality

9. **Test with MCP Inspector**:
   ```bash
   npx @modelcontextprotocol/inspector hitl-mcp
   ```
   - Verify all tools are available
   - Test each tool manually
   - Verify schemas are correct

### Phase 4: Release

10. **Create Git Tag**:
    ```bash
    git tag -a vX.Y.Z -m "Release version X.Y.Z"
    git push origin vX.Y.Z
    ```

11. **Publish to PyPI**:
    ```bash
    uv publish
    ```
    - Requires PyPI credentials
    - Verify publication succeeds
    - Check package on PyPI

12. **Create GitHub Release**:
    - Go to GitHub releases
    - Create new release from tag
    - Use CHANGELOG content for release notes
    - Attach built artifacts (optional)

### Phase 5: Post-Release

13. **Verification**:
    ```bash
    # Test installation from PyPI
    pip install hitl-mcp-cli==X.Y.Z
    hitl-mcp --version
    ```

14. **Communication**:
    - Announce on GitHub Discussions
    - Update any external documentation
    - Notify stakeholders

15. **Next Development**:
    - Bump version to next development version
    - Add "Unreleased" section to CHANGELOG
    - Continue development

## Emergency Rollback

If issues are discovered after release:

1. **Yank the release from PyPI**:
   ```bash
   # PyPI allows yanking (hiding) releases
   # Users with pinned versions can still install
   ```

2. **Publish hotfix**:
   - Create hotfix branch
   - Fix critical issue
   - Bump patch version
   - Follow abbreviated release process

## Output Format

```
🚀 Deployment Checklist
━━━━━━━━━━━━━━━━━━━━━

Current Version: 0.4.0
Target Version: [Ask user]

Phase 1: Pre-Release Validation
✅ Version determined: X.Y.Z
✅ All tests pass
✅ All quality checks pass
✅ Documentation complete

Phase 2: Build Preparation
✅ Version updated
✅ CHANGELOG updated
✅ Changes committed

Phase 3: Build & Test
✅ Package built
✅ Installation tested
✅ MCP tools verified

Phase 4: Release
✅ Git tag created
✅ Published to PyPI
✅ GitHub release created

Phase 5: Post-Release
✅ Installation verified
✅ Communication sent

🎉 Release vX.Y.Z completed successfully!
```

## Important Notes

- **Never rush a release** - all checks must pass
- **Test thoroughly** - bugs in releases affect users
- **Document everything** - CHANGELOG is critical
- **Semantic versioning** - breaking changes = major bump
- **Communication** - users need to know about changes
