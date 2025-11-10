# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.3.x   | :white_check_mark: |
| 0.2.x   | :x:                |
| < 0.2   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them via email to: geehexx@gmail.com

You should receive a response within 48 hours. If for some reason you do not, please follow up via email to ensure we received your original message.

Please include the following information:

- Type of issue (e.g., buffer overflow, SQL injection, cross-site scripting, etc.)
- Full paths of source file(s) related to the manifestation of the issue
- The location of the affected source code (tag/branch/commit or direct URL)
- Any special configuration required to reproduce the issue
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact of the issue, including how an attacker might exploit it

## Security Best Practices for Users

### Network Security
- Bind to localhost (127.0.0.1) by default - never expose to public internet
- Use firewall rules to restrict access
- Run behind VPN for remote access

### Input Validation
- Review all prompts before responding
- Be cautious with path inputs - verify they're within expected directories
- Use regex validation patterns carefully to avoid ReDoS attacks

### Deployment Security
- Run as non-root user
- Use environment variables for configuration (not command-line args in logs)
- Enable audit logging in production
- Monitor for unusual activity

### Dependency Security
- Keep dependencies updated (use dependabot)
- Review dependency changes before updating
- Use `pip-audit` or similar tools to scan for vulnerabilities

## Security Scanning

This project uses:
- **Bandit**: Static security analysis for Python code
- **Dependabot**: Automated dependency updates
- **MyPy**: Type checking to prevent type-related bugs

Run security scan locally:
```bash
uv run bandit -r hitl_mcp_cli/
```
