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

### Visual Separator State Management - Known Limitation 2025-11-10

**Problem:** Visual separators use global state (`_needs_separator`) which is not thread-safe for concurrent tool calls.

**Current Behavior:**
- Works correctly for sequential prompts (typical HITL usage)
- May show inconsistent separators if multiple prompts execute concurrently
- Global state accessed from thread executor (sync_to_async wrapper)

**Impact:** Low - HITL prompts are typically sequential (human response time prevents concurrency)

**Proper Solution:**
- Replace global state with request-scoped state (passed as parameter)
- Use context manager for separator state
- Or use thread-local storage with proper synchronization

**Implementation Notes:**
- File to modify: `hitl_mcp_cli/ui/prompts.py`
- Add `_separator_context` parameter to all prompt functions
- Or implement context manager: `with separator_context():`
- Requires API change (breaking change for direct prompt function calls)

**Workaround:** Current implementation is acceptable for typical HITL usage where prompts are sequential.

**Priority:** Low - works for intended use case, but should be fixed for architectural correctness

**Effort:** 2-3 hours (requires API redesign and testing)

### Terminal Output Border - Deferred 2025-11-10

**Problem:** Terminal output lacks visual containment - prompts and responses blend with surrounding terminal content.

**Proposed Solution:** Wrap entire CLI interaction area in a visual border using Rich's Panel or Layout system.

**Implementation Notes:**

- File to modify: `hitl_mcp_cli/ui/prompts.py`
- Requires refactoring console usage to use a single Panel/Layout container
- All prompts and notifications would render inside this container
- Challenge: InquirerPy prompts may not work well inside Rich containers

**Blockers:**

- Requires significant refactoring (30+ minutes)
- InquirerPy and Rich integration complexity
- May interfere with terminal scrolling behavior

**Priority:** Low - cosmetic enhancement, current UI is functional

### Auto-Scroll to Latest Prompt - Deferred 2025-11-10

**Problem:** In long sessions with many prompts, newest prompt may be off-screen requiring manual scrolling.

**Proposed Solution:** Automatically scroll terminal to show latest prompt.

**Implementation Notes:**

- Terminal scrolling is controlled by terminal emulator, not Python application
- Investigated options: InquirerPy, Rich, curses library
- No reliable cross-platform solution found

**Blockers:**

- Terminal emulator controls scrolling, not application
- Would require terminal-specific escape sequences (not portable)
- May interfere with user's terminal preferences

**Workarounds:**

- Users can manually scroll or use terminal's "scroll to bottom" feature
- Visual separators (implemented) help identify new prompts
- Most terminal emulators auto-scroll on new output

**Priority:** Low - terminal emulator limitation, not application issue

### Context Field for Prompts - Deferred 2025-11-10

**Problem:** Agents sometimes need to provide additional context about why input is needed, beyond the prompt text.

**Proposed Solution:** Add optional `context` parameter to all tools that displays in a muted panel above the prompt.

**Implementation Notes:**

- Add `context: str | None = None` parameter to each tool in `server.py`
- Modify prompt functions to accept and display context
- Example:

  ```python
  if context:
      console.print(Panel(context, title="Context", border_style="dim", padding=(1, 2)))
  ```

**Blockers:**

- Requires MCP protocol change (new parameter in tool schema)
- Requires agent adoption (agents must learn to use context parameter)
- May add visual clutter if overused

**Priority:** Medium - useful feature but requires ecosystem coordination

**Alternative:** Agents can include context in the prompt text itself (current approach).

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
- Health check endpoint (/health) - **DEFERRED**: MCP protocol includes built-in `ping` utility for health checks. Custom HTTP endpoints are not standard MCP practice and over-engineer for local dev tool use case. Only needed if HITL is deployed as shared production service (rare). Use MCP `ping` for health monitoring.
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
- [x] Configuration management (env vars) ✅ DONE
- [x] Structured logging with levels ✅ DONE
- [ ] Health monitoring (use MCP `ping` utility, not custom endpoint)
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

## Plugin Architecture

**Status**: Plugin framework development moved to dedicated repository.

HITL MCP CLI will gain plugin support through the **[MCP Plugin Server](https://github.com/geehexx/mcp-plugin-server)** framework. This generic, reusable framework enables:

- Plugin-based extensibility for any MCP server
- Wrapper mode to enhance existing MCP servers
- Standalone mode to build complete servers from plugins
- Robust validation and per-plugin logging

See the [MCP Plugin Server documentation](https://github.com/geehexx/mcp-plugin-server/tree/main/docs) for comprehensive details on:

- Plugin architecture and design
- API specifications and contracts
- Implementation guide and examples
- Integration path for HITL

### HITL-Specific Plugin Enhancements

Once the plugin framework is ready, HITL-specific enhancements to consider:

#### Web UI Plugin

- Browser-based interface for remote access
- WebSocket for real-time updates
- Mobile-responsive design

#### Slack Integration Plugin

- Post prompts as Slack messages
- Interactive components (buttons, select menus)
- Team collaboration and audit trail

#### AI Router Plugin (RITL/NITL)

- AI-powered decision routing
- Confidence-based escalation to humans
- Learning from past interactions

## UI/UX Audit - 2025-11-10

### Current Strengths

**Visual Design:**

- ✅ Consistent icon system across all prompt types (✏️, 🎯, ☑️, ❓, 📁)
- ✅ Color-coded notifications (green=success, blue=info, yellow=warning, red=error)
- ✅ Rich formatting with panels and styled text
- ✅ Gradient banner with clear server information
- ✅ Visual separators between prompts (implemented 2025-11-10)
- ✅ Markdown rendering support (implemented 2025-11-10)

**Interaction Design:**

- ✅ Clear instructions for multiline input ("Press Esc+Enter to submit")
- ✅ Checkbox instructions ("Space to select, Enter to confirm")
- ✅ Default values shown in prompts
- ✅ Validation feedback at input time
- ✅ Keyboard-driven interface (no mouse required)

**Information Architecture:**

- ✅ Prompts clearly separated from responses
- ✅ Notifications visually distinct from prompts
- ✅ Icon system provides quick visual scanning
- ✅ Consistent prompt structure across all types

### Improvement Opportunities

**Visual Enhancements (Low Priority):**

- **Font rendering:** Currently relies on terminal font - no control over typography
  - Effort: N/A (terminal limitation)
  - Impact: Low (users choose their preferred terminal font)

- **Spacing/padding:** Could add more breathing room between elements
  - Effort: 15 minutes (adjust Panel padding values)
  - Impact: Low (current spacing is functional)

- **Color contrast:** Current colors work well but could be tested for accessibility
  - Effort: 30 minutes (test with color blindness simulators)
  - Impact: Medium (affects accessibility)

- **Animation:** Could add subtle animations for state transitions
  - Effort: 2-3 hours (requires Rich animation features)
  - Impact: Low (cosmetic, may be distracting)

**Interaction Improvements (Medium Priority):**

- **Undo/edit:** No way to edit previous responses
  - Effort: High (requires state management and UI redesign)
  - Impact: Medium (users can cancel and restart)
  - Blocker: MCP protocol doesn't support editing past responses

- **History navigation:** No way to review previous prompts/responses
  - Effort: Medium (2-3 hours for in-memory history)
  - Impact: Medium (terminal scrollback provides this)

- **Keyboard shortcuts:** Could add shortcuts for common actions
  - Effort: Medium (1-2 hours per shortcut)
  - Impact: Low (current keyboard nav is sufficient)

- **Search/filter:** For long choice lists in selections
  - Effort: Low (InquirerPy supports this with `filter` parameter)
  - Impact: Medium (useful for 20+ choices)
  - Implementation: Add `filter=True` to select/checkbox prompts when len(choices) > 15

**Accessibility Concerns (High Priority):**

- **Screen reader support:** Unknown compatibility with screen readers
  - Effort: 4-6 hours (testing + fixes)
  - Impact: High (critical for accessibility)
  - Action: Test with NVDA, JAWS, VoiceOver
  - Concern: Rich formatting may not translate well to screen readers

- **Color blindness:** Current color scheme not tested for color blindness
  - Effort: 1 hour (test with simulators)
  - Impact: High (affects 8% of males, 0.5% of females)
  - Action: Test with Coblis or similar tool
  - Mitigation: Icons provide non-color visual cues

- **High contrast mode:** No dedicated high contrast theme
  - Effort: 2-3 hours (implement theme system)
  - Impact: Medium (terminal high contrast modes may suffice)

- **Keyboard-only navigation:** ✅ Already fully keyboard-driven

- **Font size:** Relies on terminal font size settings
  - Effort: N/A (terminal limitation)
  - Impact: Low (users control terminal font size)

**Information Architecture (Low Priority):**

- **Prompt grouping:** Related prompts could be visually grouped
  - Effort: Medium (1-2 hours)
  - Impact: Low (current separators provide structure)

- **Progress indicators:** For multi-step workflows
  - Effort: Medium (2-3 hours)
  - Impact: Medium (useful for complex workflows)
  - Example: "Step 2 of 5: Select deployment environment"

- **Breadcrumbs:** Show context of current prompt in larger workflow
  - Effort: High (requires workflow state management)
  - Impact: Low (agents can include context in prompts)

### Proposed Enhancements with Effort Estimates

**Quick Wins (< 1 hour):**

1. ✅ **DONE (v0.5.0)**: **Search/filter for long choice lists** - 30 min
   - Added `filter_enable=True` when len(choices) > 15
   - Added `max_height="70%"` to prevent overwhelming display
   - Improves UX for large selection lists

2. ✅ **DONE (v0.5.0)**: **Color blindness testing** - 1 hour
   - Tested current colors with simulator
   - Documented findings in docs/ACCESSIBILITY.md
   - Verified icons provide sufficient non-color cues

**Medium Effort (1-4 hours):**
3. **High contrast theme** - 2-3 hours

- Implement theme system with environment variable
- Create high contrast color palette
- Test with accessibility tools

4. **Progress indicators** - 2-3 hours
   - Add optional `step` and `total_steps` parameters
   - Display "Step X of Y" in prompt header
   - Useful for multi-step workflows

5. **Screen reader testing** - 4 hours
   - Test with NVDA, JAWS, VoiceOver
   - Document compatibility issues
   - Fix critical issues

**Large Effort (> 4 hours):**
6. **History/review feature** - 6-8 hours

- In-memory history of prompts and responses
- Keyboard shortcut to view history
- Export history to file

7. **Undo/edit system** - 8-12 hours
   - State management for responses
   - UI for editing previous responses
   - MCP protocol extension (if needed)

### Accessibility Action Plan

**Phase 1: Assessment (2 hours)**

- Test with color blindness simulators
- Test with screen readers (NVDA, VoiceOver)
- Document compatibility issues

**Phase 2: Quick Fixes (2-3 hours)**

- Ensure all visual information has non-color cues (icons ✅)
- Add ARIA labels if screen reader issues found
- Improve contrast ratios if needed

**Phase 3: Advanced Features (4-6 hours)**

- Implement high contrast theme
- Add screen reader optimizations
- Create accessibility documentation

**Priority:** High - accessibility is critical for inclusive software

### Recommended Next Steps

1. **Immediate (this sprint):**
   - Color blindness testing (1 hour)
   - Add search/filter for long lists (30 min)

2. **Short-term (next month):**
   - Screen reader testing and fixes (4 hours)
   - High contrast theme (3 hours)

3. **Long-term (future releases):**
   - Progress indicators (3 hours)
   - History feature (8 hours)

4. **Deferred (low priority):**
   - Animation system
   - Undo/edit system
   - Advanced keyboard shortcuts

## Evaluation Criteria

When considering any enhancement:

1. **Does it solve a real problem?** Not just "nice to have"
2. **Does it maintain simplicity?** Complexity is the enemy
3. **Is it agent-friendly?** Will LLMs understand how to use it?
4. **Is it maintainable?** Can we support it long-term?
5. **Does it fit the core mission?** Human-in-the-loop input collection

If the answer to any question is "no" or "maybe", defer the enhancement.

## Implementation Priority

### High Priority (Production Blockers)

- Configuration management (env vars) ✅ DONE
- Structured logging ✅ DONE
- Health monitoring: Use MCP `ping` utility (built-in protocol feature)

**Note**: Most "production blocker" items are only relevant if HITL is deployed as a shared production service. For typical local development use (the primary use case), configuration management and logging are sufficient.

### Medium Priority (Production Nice-to-Have)

- Metrics collection
- Audit logging
- Performance benchmarks

### Low Priority (Future Enhancements)

- Advanced UI features
- New tool types
- Integration examples
- Plugin support (depends on [mcp-plugin-server](https://github.com/geehexx/mcp-plugin-server))
