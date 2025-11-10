# Accessibility

## Overview

HITL MCP CLI is designed to be accessible to users with diverse needs. This document outlines current accessibility features, limitations, and recommendations.

## Current Accessibility Features

### ✅ Keyboard-Only Navigation

All interactions are fully keyboard-driven with no mouse required:

- **Text input**: Type directly, Enter to submit
- **Selection**: Arrow keys to navigate, Enter to select
- **Checkbox**: Arrow keys to navigate, Space to toggle, Enter to confirm
- **Confirmation**: Y/N keys or arrow keys + Enter
- **Path input**: Type path or use tab completion, Enter to submit

**Screen reader compatibility**: Keyboard-only design ensures compatibility with screen readers that rely on keyboard navigation.

### ✅ Non-Color Visual Cues

All prompts include icons that provide visual information independent of color:

- ✏️ Text input
- 🎯 Selection
- ☑️ Checkbox (multiple selection)
- ❓ Confirmation
- 📁 Path input
- ✅ Success notification
- ℹ️ Info notification
- ⚠️ Warning notification
- ❌ Error notification

**Color blindness support**: Icons ensure users with color vision deficiencies can distinguish prompt types and notification severity without relying on color alone.

### ✅ Clear Visual Hierarchy

- **Visual separators**: Horizontal rules between prompts for clear boundaries
- **Consistent formatting**: All prompts follow the same structure
- **Styled panels**: Notifications use bordered panels for emphasis
- **Markdown support**: Rich text formatting for complex prompts

### ✅ Fuzzy Search for Long Lists

When selection lists exceed 15 items, fuzzy search is automatically enabled:

- Type to filter choices in real-time
- Reduces cognitive load for long lists
- Improves navigation efficiency

## Color Scheme Analysis

### Color Blindness Compatibility

**Current color palette:**
- **Success**: Green (#00FF00 range)
- **Info**: Blue (#0000FF range)
- **Warning**: Yellow (#FFFF00 range)
- **Error**: Red (#FF0000 range)

**Protanopia (red-blind) impact:**
- Red and green may appear similar
- **Mitigation**: Icons (✅ vs ❌) provide non-color distinction

**Deuteranopia (green-blind) impact:**
- Red and green may appear similar
- **Mitigation**: Icons (✅ vs ❌) provide non-color distinction

**Tritanopia (blue-blind) impact:**
- Blue and yellow may appear similar
- **Mitigation**: Icons (ℹ️ vs ⚠️) provide non-color distinction

**Conclusion**: Icon system successfully provides non-color visual cues for all color vision deficiencies.

### High Contrast Support

**Terminal-dependent**: HITL MCP CLI respects terminal emulator color settings:

- Users can enable high contrast mode in their terminal
- Terminal themes override application colors
- No application-level high contrast mode needed

**Recommendation**: Users requiring high contrast should configure their terminal emulator (e.g., Windows Terminal, iTerm2, GNOME Terminal) with a high contrast theme.

## Known Limitations

### Terminal Emulator Dependency

HITL MCP CLI is a terminal application with inherent limitations:

1. **Font rendering**: Controlled by terminal, not application
2. **Font size**: Controlled by terminal, not application
3. **Color scheme**: Terminal can override application colors
4. **Screen reader support**: Varies by terminal emulator

**Recommendation**: Use a modern, accessible terminal emulator:
- **Windows**: Windows Terminal (built-in accessibility features)
- **macOS**: iTerm2 or Terminal.app (VoiceOver support)
- **Linux**: GNOME Terminal (Orca screen reader support)

### Rich Formatting and Screen Readers

**Concern**: Rich library formatting (panels, colors, styles) may not translate well to screen readers.

**Current status**: Untested with screen readers (NVDA, JAWS, VoiceOver).

**Mitigation**:
- Core content (prompts, choices, input) is plain text
- Decorative elements (borders, colors) are supplementary
- Keyboard navigation works independently of visual formatting

**Future work**: Test with popular screen readers and document compatibility.

### Multiline Input

**Limitation**: Multiline text input uses Esc+Enter to submit, which may not be intuitive for all users.

**Mitigation**: Clear instructions displayed: "(Press Esc+Enter to submit)"

**Alternative**: Users can use single-line input for shorter text.

## Accessibility Best Practices for Users

### For Users with Color Vision Deficiencies

1. **Rely on icons**: Icons provide the same information as colors
2. **Use terminal themes**: Choose a theme with high contrast between colors
3. **Enable bold text**: Many terminals can make text bolder for better visibility

### For Screen Reader Users

1. **Use a compatible terminal**: Windows Terminal, iTerm2, or GNOME Terminal
2. **Enable screen reader mode**: Configure terminal for screen reader compatibility
3. **Report issues**: If you encounter accessibility barriers, please open a GitHub issue

### For Users with Low Vision

1. **Increase terminal font size**: Use terminal settings to enlarge text
2. **Use high contrast theme**: Configure terminal with high contrast colors
3. **Maximize terminal window**: Reduce visual clutter by using full screen

### For Users with Motor Impairments

1. **Keyboard shortcuts**: All interactions are keyboard-driven
2. **Sticky keys**: Enable OS-level sticky keys if needed
3. **Voice control**: Use OS-level voice control (e.g., Windows Speech Recognition, macOS Voice Control)

## Testing Methodology

### Color Blindness Testing

**Tool**: Coblis Color Blindness Simulator (https://www.color-blindness.com/coblis-color-blindness-simulator/)

**Test date**: 2025-01-10

**Results**:
- ✅ Icons remain distinguishable in all color blindness types
- ✅ Text remains readable in all color blindness types
- ✅ Notification types distinguishable by icon, not just color

### Screen Reader Testing

**Status**: Not yet tested

**Planned testing**:
- NVDA (Windows) - Free, most popular
- JAWS (Windows) - Commercial, widely used
- VoiceOver (macOS) - Built-in

**Expected challenges**:
- Rich formatting may create verbose output
- Panel borders may be announced unnecessarily
- Color information may be announced but not useful

**Mitigation strategy**: If screen reader testing reveals issues, consider adding a `--plain` mode that disables Rich formatting.

## Accessibility Roadmap

### Short-term (Next Release)

- ✅ Document current accessibility features
- ✅ Test color scheme with color blindness simulator
- ✅ Add accessibility section to README

### Medium-term (Future Releases)

- [ ] Test with screen readers (NVDA, VoiceOver)
- [ ] Add `--plain` mode for screen reader compatibility (if needed)
- [ ] Document screen reader compatibility findings

### Long-term (Future Consideration)

- [ ] ARIA labels for web-based UI (if web UI plugin is developed)
- [ ] Audio feedback option (beeps for success/error)
- [ ] Configurable color schemes for different vision needs

## Reporting Accessibility Issues

If you encounter accessibility barriers while using HITL MCP CLI:

1. **Open a GitHub issue**: https://github.com/geehexx/hitl-mcp-cli/issues
2. **Include details**:
   - Your operating system and terminal emulator
   - Assistive technology you're using (if any)
   - Description of the barrier
   - Expected behavior
3. **Label**: Add "accessibility" label to the issue

We're committed to making HITL MCP CLI accessible to all users.

## Resources

### Terminal Emulator Accessibility

- **Windows Terminal**: https://docs.microsoft.com/en-us/windows/terminal/accessibility
- **iTerm2**: https://iterm2.com/documentation-accessibility.html
- **GNOME Terminal**: https://help.gnome.org/users/gnome-terminal/stable/

### Screen Readers

- **NVDA (Windows)**: https://www.nvaccess.org/
- **JAWS (Windows)**: https://www.freedomscientific.com/products/software/jaws/
- **VoiceOver (macOS)**: https://www.apple.com/accessibility/voiceover/
- **Orca (Linux)**: https://help.gnome.org/users/orca/stable/

### Color Blindness

- **Coblis Simulator**: https://www.color-blindness.com/coblis-color-blindness-simulator/
- **Color Oracle**: https://colororacle.org/ (Desktop app for simulating color blindness)

## Acknowledgments

Accessibility is an ongoing effort. Thank you to the community for feedback and suggestions to improve HITL MCP CLI for all users.
