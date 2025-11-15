---
description: Run comprehensive security checks and scans
---

# Security Checks and Scans

Comprehensive security scanning and validation for HITL MCP CLI.

## Your Task

Perform thorough security checks on the codebase.

### 1. Security Scanner (Bandit)

```bash
uv run bandit -r hitl_mcp_cli/ -f screen
```

**Check for:**
- Use of assert (production code)
- Hardcoded passwords or secrets
- SQL injection vulnerabilities
- Shell injection vulnerabilities
- Insecure cryptography
- Unsafe YAML/pickle usage

**Report:**
- High severity issues (must fix)
- Medium severity issues (should fix)
- Low severity issues (review)

### 2. Dependency Security Audit

```bash
uv pip audit
```

**Check for:**
- Known CVEs in dependencies
- Outdated packages with security fixes
- Deprecated packages

**Actions:**
- List all vulnerable dependencies
- Show severity levels
- Recommend updates or alternatives

### 3. Secrets Scanning

**Check for hardcoded secrets:**
```bash
git grep -iE '(password|api_key|secret|token|credential).*=.*["\047]' -- '*.py'
```

**Check for:**
- API keys
- Passwords
- Tokens
- Private keys
- Credentials

**Verify .gitignore includes:**
- `.env`, `.envrc`
- `credentials.json`
- `*.key`, `*.pem`
- `config.local.*`

### 4. Input Validation Review

**Review all user inputs:**
1. **Text inputs:**
   - Regex validation where appropriate
   - Length limits
   - Character whitelisting

2. **Path inputs:**
   - Path traversal prevention (no `..`)
   - Absolute path validation
   - Existence checking

3. **Shell commands:**
   - Proper quoting (`shlex.quote`)
   - No direct user input in shell
   - Whitelist allowed commands

### 5. MCP Tool Security

**For each MCP tool:**
- [ ] Input validation present
- [ ] Error messages don't leak sensitive info
- [ ] No command injection vectors
- [ ] Proper error handling
- [ ] Timeout protection

### 6. Environment Variables

**Check for:**
- Proper use of `os.getenv()`
- No defaults for sensitive values
- Documentation of required vars
- No secrets in code

### 7. File Operations

**Review all file operations:**
- Use context managers (`with` statements)
- Validate paths before operations
- Proper permission handling
- No race conditions (TOCTOU)

### 8. Dependency Review

**Check `pyproject.toml`:**
```bash
uv pip list
```

- All dependencies are necessary
- Versions are pinned or bounded
- No deprecated packages
- Licenses are compatible
- Sources are trusted (PyPI)

### 9. Git History Scan

**Check for accidentally committed secrets:**
```bash
git log -p | grep -iE '(password|api_key|secret|token|credential)' | head -20
```

**If found:**
- Identify the commits
- Recommend git-filter-repo or BFG
- Rotate any exposed credentials

### 10. SECURITY.md Compliance

**Verify:**
- Security policy is up to date
- Contact information is correct
- Disclosure process is clear
- Response timeline is realistic

## Security Best Practices

**Code Level:**
- ✅ Never trust user input
- ✅ Validate all inputs
- ✅ Use parameterized queries (if SQL)
- ✅ Escape shell variables
- ✅ Use secure random (secrets module)
- ✅ No eval() or exec()
- ✅ Proper error handling (no info leakage)

**Deployment Level:**
- ✅ Environment variables for secrets
- ✅ Principle of least privilege
- ✅ Regular dependency updates
- ✅ Security headers if applicable
- ✅ Rate limiting for APIs

**Development Level:**
- ✅ Pre-commit hooks for secrets
- ✅ Regular security audits
- ✅ Dependency scanning in CI
- ✅ Code review for security

## Output Format

```
🔒 Security Scan Report
━━━━━━━━━━━━━━━━━━━━━

Bandit Static Analysis:
✅ No high severity issues
✅ No medium severity issues
ℹ️  2 low severity issues (informational)

Dependency Audit:
✅ No known vulnerabilities
✅ All dependencies up to date

Secrets Scanning:
✅ No hardcoded secrets found
✅ .gitignore properly configured

Input Validation:
✅ All user inputs validated
✅ Path traversal prevention in place
✅ Shell injection prevention verified

MCP Tool Security:
✅ All tools have input validation
✅ Error handling is secure
✅ No information leakage

Environment Variables:
✅ Proper usage of os.getenv()
✅ No default secrets

File Operations:
✅ Context managers used
✅ Paths validated
✅ No race conditions

Git History:
✅ No secrets in commit history

Overall Security: ✅ EXCELLENT

Recommendations:
[Any suggestions for improvement]
```

## Critical Issues

If critical security issues are found:

1. **Stop and report immediately**
2. **Do not commit the code**
3. **Assess the severity**:
   - High: Data exposure, RCE, privilege escalation
   - Medium: Potential vulnerabilities
   - Low: Best practice violations

4. **Fix high severity issues first**
5. **Test the fixes**
6. **Document in SECURITY.md if applicable**

## Regular Security Maintenance

**Weekly:**
- Run `uv pip audit`
- Check for dependency updates

**Monthly:**
- Full security scan (this command)
- Review SECURITY.md
- Update dependencies

**Before releases:**
- Complete security audit
- Dependency vulnerability scan
- Code review focusing on security
- Update security documentation
