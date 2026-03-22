"""Example usage of hitl-mcp-cli tools."""

import asyncio

from hitl_mcp_cli.server import hitl_choose, hitl_collect, hitl_confirm, hitl_notify


async def main() -> None:
    """Run example interactions."""
    print("=== Interactive MCP Server Example ===\n")

    # Text input
    name = await hitl_collect(message="What is your name?", default="User")
    print(f"Hello, {name}!\n")

    # Selection
    choice = await hitl_choose(
        message="Choose your favorite color:",
        choices=["Red", "Green", "Blue", "Yellow"],
        default="Blue",
    )
    print(f"You chose: {choice}\n")

    # Multiple selection
    hobbies = await hitl_choose(
        message="Select your hobbies (space to select, enter to confirm):",
        choices=["Reading", "Gaming", "Sports", "Music", "Coding"],
        multiple=True,
    )
    print(f"Your hobbies: {', '.join(hobbies) if isinstance(hobbies, list) else hobbies}\n")

    # Confirmation
    result = await hitl_confirm(message="Do you want to continue?", default=True)
    if result["action"] != "accept":
        print("Cancelled by user")
        return

    # Path input
    path = await hitl_collect(message="Enter a directory path:", input_type="path", default=".")
    print(f"Selected path: {path}\n")

    # Notification
    await hitl_notify(
        title="Example Complete",
        message=f"Successfully demonstrated all interactive tools!\nUser: {name}\nColor: {choice}",
        level="success",
    )


if __name__ == "__main__":
    asyncio.run(main())
