"""Custom startup banner with gradient colors and animation."""

import time
from typing import Literal

from rich.console import Console
from rich.text import Text
from rich.align import Align
from rich.panel import Panel

console = Console()


def create_banner_text() -> str:
    """Create ASCII art banner text."""
    return """
██╗  ██╗██╗████████╗██╗         ███╗   ███╗ ██████╗██████╗ 
██║  ██║██║╚══██╔══╝██║         ████╗ ████║██╔════╝██╔══██╗
███████║██║   ██║   ██║         ██╔████╔██║██║     ██████╔╝
██╔══██║██║   ██║   ██║         ██║╚██╔╝██║██║     ██╔═══╝ 
██║  ██║██║   ██║   ███████╗    ██║ ╚═╝ ██║╚██████╗██║     
╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝    ╚═╝     ╚═╝ ╚═════╝╚═╝     
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
        # Create gradient from cyan to blue to magenta
        text = Text()
        lines = banner_text.strip().split("\n")
        colors = ["cyan", "bright_cyan", "blue", "bright_blue", "magenta", "bright_magenta"]

        for i, line in enumerate(lines):
            color = colors[i % len(colors)]
            text.append(line + "\n", style=f"bold {color}")
    else:
        text = Text(banner_text, style="bold cyan")

    # Add subtitle
    subtitle = Text("\nHuman-in-the-Loop MCP Server\n", style="italic bright_white")
    text.append(subtitle)

    # Create info panel
    info = Text()
    info.append("\n🌐 Endpoint:   ", style="bold green")
    info.append(f"http://{host}:{port}/mcp\n", style="bright_cyan underline")
    info.append("📡 Transport:  ", style="bold green")
    info.append("Streamable-HTTP\n", style="bright_cyan")
    info.append("✨ Status:     ", style="bold green")
    info.append("Ready", style="bold bright_green")
    info.append(" • Waiting for connections...\n", style="dim")

    text.append(info)

    if animate:
        # Slide-in animation
        console.clear()
        lines_list = text.plain.split("\n")
        for i in range(len(lines_list)):
            console.clear()
            partial = Text()
            for j, line in enumerate(lines_list[:i+1]):
                # Reconstruct styling
                if j < 6:  # Banner lines
                    color = ["cyan", "bright_cyan", "blue", "bright_blue", "magenta", "bright_magenta"][j % 6]
                    partial.append(line + "\n", style=f"bold {color}")
                else:
                    partial.append(line + "\n")
            console.print(partial, end="")
            time.sleep(0.03)
        time.sleep(0.2)
    else:
        console.clear()
        console.print(text)

    console.print()
