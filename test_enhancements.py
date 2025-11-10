"""Test script to manually verify new enhancements."""

import asyncio

from hitl_mcp_cli.server import notify_completion, request_confirmation, request_selection, request_text_input


async def main() -> None:
    """Test all enhancements."""
    print("=== Testing HITL MCP CLI Enhancements ===\n")

    # Test 1: Visual separators
    print("TEST 1: Visual Separators")
    print("You should see a horizontal line before each prompt after the first one.\n")

    await request_text_input(prompt="First prompt (no separator before this)", default="test1")

    await notify_completion(
        title="Notification Test",
        message="This should trigger a separator before next prompt",
        notification_type="info",
    )

    await request_text_input(prompt="Second prompt (separator should appear above)", default="test2")

    # Test 2: Markdown rendering
    print("\nTEST 2: Markdown Rendering")
    print("The next prompt should render with markdown formatting.\n")

    markdown_prompt = """
# Choose Your Deployment Strategy

We have **three options** available:

1. **Fast Deploy** - Immediate deployment (⚠️ risky)
2. **Safe Deploy** - Includes rollback plan (✅ recommended)
3. **Staged Deploy** - Deploy to staging first

Which would you prefer?
"""

    await request_selection(
        prompt=markdown_prompt,
        choices=["Fast Deploy", "Safe Deploy", "Staged Deploy"],
        default="Safe Deploy",
    )

    # Test 3: Checkbox visibility with instruction
    print("\nTEST 3: Checkbox Visibility")
    print("All choices should be visible. Instruction text should appear.\n")

    features = await request_selection(
        prompt="Select features to enable:",
        choices=[
            "Feature A: Authentication",
            "Feature B: Caching",
            "Feature C: Logging",
            "Feature D: Monitoring",
            "Feature E: Analytics",
        ],
        allow_multiple=True,
    )
    print(f"Selected: {features}\n")

    # Test 4: Markdown in confirmation
    print("\nTEST 4: Markdown in Confirmation")

    markdown_confirm = """
## ⚠️ Destructive Operation Warning

This will **delete 50 files** including:
- `old_config.yaml`
- `deprecated_module.py`
- All files in `legacy/` directory

This action **cannot be undone**.
"""

    confirmed = await request_confirmation(prompt=markdown_confirm, default=False)
    print(f"Confirmed: {confirmed}\n")

    # Test 5: Escape key handling
    print("\nTEST 5: Escape Key Handling")
    print("Try pressing Ctrl+C to cancel the next prompt.\n")

    try:
        await request_text_input(prompt="Press Ctrl+C to test cancellation", default="or enter text")
        print("Input received successfully\n")
    except Exception as e:
        print(f"Caught exception: {e}\n")

    # Final notification
    await notify_completion(
        title="Testing Complete",
        message="All enhancements have been tested!\n\nNew features:\n- Visual separators ✅\n- Markdown rendering ✅\n- Checkbox improvements ✅\n- Escape handling ✅",
        notification_type="success",
    )


if __name__ == "__main__":
    asyncio.run(main())
