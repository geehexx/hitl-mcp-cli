"""Custom startup banner with gradient colors and animation."""

import time
from typing import Literal

from rich.console import Console
from rich.text import Text

console = Console()


def create_banner_text() -> str:
    """Create ASCII art banner text."""
    return """
╦ ╦╦╔╦╗╦    ╔╦╗╔═╗╔═╗
╠═╣║ ║ ║    ║║║║  ╠═╝
╩ ╩╩ ╩ ╩═╝  ╩ ╩╚═╝╩  
"""


def display_banner(
    host: str = "127.0.0.1",
    port: int = 5555,
    animate: bool = True,
    style: Literal["gradient", "simple"] = "gradient",
) -> None:
    """Display startup banner with gradient colors.

    Args:
        host: Server host address
        port: Server port number
        animate: Whether to animate the banner
        style: Banner style (gradient or simple)
    """
    banner_text = create_banner_text()

    if style == "gradient":
        # Create gradient from cyan to blue to purple
        text = Text()
        lines = banner_text.strip().split("\n")

        for i, line in enumerate(lines):
            # Calculate color based on line position
            if i == 0:
                text.append(line + "\n", style="bold cyan")
            elif i == 1:
                text.append(line + "\n", style="bold blue")
            else:
                text.append(line + "\n", style="bold magenta")
    else:
        text = Text(banner_text, style="bold cyan")

    # Add subtitle
    text.append("\n")
    text.append("Human-in-the-Loop MCP Server", style="dim italic")
    text.append("\n\n")

    # Add server info
    text.append("🌐 Server: ", style="bold green")
    text.append(f"http://{host}:{port}/mcp\n", style="cyan")

    text.append("📡 Transport: ", style="bold green")
    text.append("Streamable-HTTP\n", style="cyan")

    text.append("✨ Status: ", style="bold green")
    text.append("Ready for connections\n", style="green")

    if animate:
        # Simple fade-in animation
        console.clear()
        for i in range(0, 101, 20):
            console.clear()
            console.print(text, style=f"dim" if i < 100 else "")
            if i < 100:
                time.sleep(0.05)
    else:
        console.print(text)

    console.print()
