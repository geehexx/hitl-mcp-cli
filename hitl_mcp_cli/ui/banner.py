"""Custom startup banner with gradient colors."""

from rich.console import Console
from rich.text import Text

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
) -> None:
    """Display startup banner with gradient colors.

    Args:
        host: Server host address
        port: Server port number
    """
    banner_text = create_banner_text()

    # Create gradient from cyan to blue to magenta
    text = Text()
    lines = banner_text.strip().split("\n")
    colors = ["cyan", "bright_cyan", "blue", "bright_blue", "magenta", "bright_magenta"]

    for i, line in enumerate(lines):
        color = colors[i % len(colors)]
        text.append(line + "\n", style=f"bold {color}")

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

    console.clear()
    console.print(text)
    console.print()
