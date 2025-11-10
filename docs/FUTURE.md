# Future Enhancements

This document tracks potential improvements and features for future consideration. Items here are not committed work - they're ideas to evaluate when capacity allows.

## Input Validation & Sanitization

### Text Input
- **Whitespace handling**: Auto-strip leading/trailing whitespace (opt-in via parameter?)
- **Empty input validation**: Option to require non-empty input
- **Custom validators**: Allow passing validator functions beyond regex patterns
- **Multi-line formatting**: Better handling of indentation and formatting in multi-line input

**Consideration**: Adding complexity may reduce tool usefulness. Keep validation simple and predictable. Most validation should happen in the agent's logic, not the input layer.

### Path Input
- **Path normalization**: Consistent handling of `~`, `.`, `..`, symlinks
- **Path type validation**: Verify file vs directory matches expected type
- **Permission checks**: Warn if path isn't readable/writable
- **Glob pattern support**: Allow selecting multiple files with patterns

**Consideration**: Current path validation is minimal by design. Expanding it requires careful thought about cross-platform compatibility and user expectations.

## User Experience

### Timeout Handling
- **Progress indicators**: Show elapsed time for long-running prompts
- **Timeout warnings**: Notify user if approaching client timeout (if detectable)
- **Auto-save drafts**: For long text inputs, periodically save to temp file

**Consideration**: Current approach relies on client-side infinite timeout configuration. Server-side timeout handling is complex and may not be necessary.

### Visual Improvements
- **Themes**: Support different color schemes
- **Custom icons**: Allow configuration of prompt icons
- **Rich formatting**: Support markdown in prompts and messages
- **Accessibility**: Screen reader support, high contrast mode

## Tool Enhancements

### New Tool Ideas
- **request_multiline_text**: Dedicated tool for code/long text with syntax highlighting
- **request_number**: Numeric input with range validation
- **request_date**: Date/time picker
- **request_password**: Secure password input (hidden characters)
- **request_table_input**: Structured data entry (rows/columns)

**Consideration**: Each new tool adds cognitive load for agents. Only add tools that solve common, distinct use cases.

### Existing Tool Improvements
- **request_selection**:
  - Search/filter for long choice lists
  - Nested/hierarchical choices
  - Choice descriptions separate from values
- **request_confirmation**:
  - Three-way choice (Yes/No/Cancel)
  - Require typing confirmation phrase for dangerous operations
- **notify_completion**:
  - Sound notifications (optional audio feedback)
  - Desktop notifications (OS-level)
  - Persistent notification log

### UI/UX Enhancements
- **Themes**: Allow users to customize color schemes beyond default
- **Progress bars**: For long-running operations (though HITL operations are typically instant)
- **History**: Show recent interactions in a log
- **Keyboard shortcuts**: Quick access to common actions
- **Animation controls**: More granular control over animations (speed, style)

**Consideration**: Most UI enhancements should be opt-in to maintain simplicity. The current UI is intentionally minimal and focused.

## Architecture

### Performance
- **Async optimization**: Review executor usage in sync_to_async wrapper
- **Connection pooling**: For high-frequency tool calls
- **Caching**: Cache prompt configurations for repeated calls

### Testing
- **Integration tests**: ✅ DONE - Real HTTP/MCP tests without mocking (test_mcp_integration.py)
- **Load testing**: Verify behavior under concurrent requests
- **Cross-platform testing**: Automated tests on Linux/macOS/Windows

### Documentation
- **Video tutorials**: Screen recordings of common workflows
- **Agent integration examples**: Sample code for popular agent frameworks
- **Troubleshooting guide**: ✅ DONE - Added to README

## MCP Best Practices Compliance

### Configuration Management
**Current**: CLI arguments only (--host, --port, --no-banner)
**Improvement**:
- Environment variable support (MCP_HOST, MCP_PORT, MCP_LOG_LEVEL)
- Configuration file support (.hitl-mcp.yaml)
- Pydantic-based config validation
- Per-environment config overrides

**Consideration**: Keep it simple. Most users run locally with defaults. Advanced config is for production deployments.

### Observability
**Current**: Basic ERROR-level logging
**Improvements**:
- Structured logging (JSON format for production)
- Configurable log levels per environment
- Health check endpoint (/health)
- Metrics endpoint (/metrics) with Prometheus format
- Request/response logging (opt-in for debugging)
- Performance metrics (request duration, error rates)

**Consideration**: Observability adds complexity. Implement as opt-in features for production use.

### API Versioning
**Current**: No explicit versioning
**Improvements**:
- Version in server name ("Interactive Input Server v1")
- Protocol version in responses
- Deprecation warnings for old clients
- Backward compatibility guarantees

**Consideration**: MCP protocol handles versioning. Server versioning is mainly for tracking breaking changes.

### Resilience Patterns
**Current**: Basic error handling
**Improvements**:
- Circuit breaker for external dependencies (if any added)
- Retry logic with exponential backoff
- Graceful degradation (fallback to simpler prompts)
- Request timeout configuration
- Rate limiting per client

**Consideration**: HITL servers are inherently resilient - they wait for human input. Most resilience patterns don't apply.

### Production Readiness Checklist
- [ ] Configuration management (env vars, config files)
- [ ] Structured logging with levels
- [ ] Health check endpoint
- [ ] Metrics collection
- [ ] Graceful shutdown handling
- [ ] Connection pooling (if needed)
- [ ] Request ID tracking
- [ ] Audit logging (who requested what)
- [ ] Performance benchmarks
- [ ] Load testing results
- [ ] Security audit
- [ ] Deployment documentation
- [ ] Monitoring runbook
- [ ] Incident response procedures

## Security Considerations

### Current Security Posture
- **No authentication**: Server trusts all connections on configured host/port
- **No authorization**: Any connected client can call any tool
- **No input sanitization**: User input is passed through as-is (by design)
- **No rate limiting**: No protection against rapid tool calls
- **No path restrictions**: Users can select any filesystem path they have access to

### Potential Security Enhancements

**Authentication & Authorization**
- API key validation
- Client certificate authentication
- Per-client tool access control

**Consideration**: Authentication adds complexity and may not be necessary if the server runs locally and is accessed only by trusted agents. Network-level security (firewall, VPN) may be more appropriate.

**Input Validation**
- Regex complexity limits (prevent ReDoS attacks)
- Path whitelist/blacklist (restrict filesystem access)
- Input length limits
- Content filtering (prevent injection attacks)

**Consideration**: Over-validation defeats the purpose of HITL. The human is the security boundary - they decide what input is acceptable. Validation should focus on preventing server crashes, not restricting user choice.

**Rate Limiting**
- Max requests per minute per client
- Concurrent request limits
- Backpressure mechanisms

**Consideration**: HITL operations are naturally rate-limited by human response time. Rate limiting may only be needed for public-facing deployments.

### Security Best Practices

**For Users**:
1. **Run locally**: Bind to 127.0.0.1 (default) not 0.0.0.0
2. **Use firewall**: Block external access to the server port
3. **Review prompts**: Always read what the agent is asking before responding
4. **Validate paths**: Don't blindly accept suggested file paths
5. **Use regex carefully**: Complex patterns in validate_pattern can cause performance issues

**For Deployments**:
1. **Network isolation**: Run server in isolated network segment
2. **Reverse proxy**: Use nginx/Apache with authentication if exposing over network
3. **Monitoring**: Log all tool calls for audit trail
4. **Principle of least privilege**: Run server as non-root user

## Non-Goals

Things we explicitly don't want to do:

- **GUI interface**: This is a terminal-based tool by design
- **Web interface**: Adds complexity and security concerns
- **Built-in authentication**: Should be handled at infrastructure level
- **Database storage**: Keep it stateless and simple
- **Complex workflow engine**: Not a workflow orchestrator
- **LLM integration**: This is a pure I/O tool, not an AI service

## Evaluation Criteria

When considering any enhancement:

1. **Does it solve a real problem?** Not just "nice to have"
2. **Does it maintain simplicity?** Complexity is the enemy
3. **Is it agent-friendly?** Will LLMs understand how to use it?
4. **Is it maintainable?** Can we support it long-term?
5. **Does it fit the core mission?** Human-in-the-loop input collection
6. **Is it production-ready?** Does it follow MCP best practices?

If the answer to any question is "no" or "maybe", defer the enhancement.

## Implementation Priority

### High Priority (Production Blockers)
- Configuration management (env vars)
- Health check endpoint
- Structured logging

### Medium Priority (Production Nice-to-Have)
- Metrics collection
- Audit logging
- Performance benchmarks

### Low Priority (Future Enhancements)
- Advanced UI features
- New tool types
- Integration examples
