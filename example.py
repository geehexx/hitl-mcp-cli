"""Example usage of hitl-mcp-cli tools."""

import asyncio

from hitl_mcp_cli.server import (
    notify_completion,
    request_confirmation,
    request_path_input,
    request_selection,
    request_text_input,
)


async def main() -> None:
    """Run example interactions."""
    print("=== Interactive MCP Server Example ===\n")

    # Text input
    name = await request_text_input(prompt="What is your name?", default="User")
    print(f"Hello, {name}!\n")

    # Selection
    choice = await request_selection(
        prompt="Choose your favorite color:",
        choices=["Red", "Green", "Blue", "Yellow"],
        default="Blue",
    )
    print(f"You chose: {choice}\n")

    # Multiple selection
    hobbies = await request_selection(
        prompt="Select your hobbies (space to select, enter to confirm):",
        choices=["Reading", "Gaming", "Sports", "Music", "Coding"],
        allow_multiple=True,
    )
    print(f"Your hobbies: {', '.join(hobbies)}\n")

    # Confirmation
    confirmed = await request_confirmation(prompt="Do you want to continue?", default=True)
    if not confirmed:
        print("Cancelled by user")
        return

    # Path input
    path = await request_path_input(
        prompt="Enter a directory path:", path_type="directory", must_exist=False, default="."
    )
    print(f"Selected path: {path}\n")

    # Notification
    await notify_completion(
        title="Example Complete",
        message=f"Successfully demonstrated all interactive tools!\nUser: {name}\nColor: {choice}",
        notification_type="success",
    )


if __name__ == "__main__":
    asyncio.run(main())
