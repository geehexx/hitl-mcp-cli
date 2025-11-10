"""Generate visual examples for documentation."""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax

console = Console(record=True, width=100)


def generate_banner_example() -> str:
    """Generate banner visual."""
    text = Text()
    text.append("██╗  ██╗██╗████████╗██╗         ███╗   ███╗ ██████╗██████╗\n", style="bold cyan")
    text.append("██║  ██║██║╚══██╔══╝██║         ████╗ ████║██╔════╝██╔══██╗\n", style="bold bright_cyan")
    text.append("███████║██║   ██║   ██║         ██╔████╔██║██║     ██████╔╝\n", style="bold blue")
    text.append("\nHuman-in-the-Loop MCP Server\n", style="italic bright_white")
    text.append("\n🌐 Endpoint:   ", style="bold green")
    text.append("http://127.0.0.1:5555/mcp\n", style="bright_cyan underline")
    text.append("✨ Status:     ", style="bold green")
    text.append("Ready", style="bold bright_green")
    
    console.print(text)
    return console.export_text()


def generate_prompt_examples() -> str:
    """Generate prompt examples."""
    console.print("\n[bold cyan]Text Input Prompt:[/bold cyan]")
    console.print("✏️  Enter your name: [dim](John Doe)[/dim]")
    
    console.print("\n[bold cyan]Selection Prompt:[/bold cyan]")
    console.print("🎯 Choose deployment environment:")
    console.print("  [cyan]❯[/cyan] Development")
    console.print("    Staging")
    console.print("    Production")
    
    console.print("\n[bold cyan]Confirmation Prompt:[/bold cyan]")
    console.print("❓ Delete all files? [dim](y/N)[/dim]")
    
    console.print("\n[bold cyan]Success Notification:[/bold cyan]")
    panel = Panel(
        "Successfully deployed to production",
        title="[bold green]✅ Deployment Complete[/bold green]",
        border_style="green",
        padding=(1, 2)
    )
    console.print(panel)
    
    return console.export_text()


if __name__ == "__main__":
    print("=== Banner Example ===")
    print(generate_banner_example())
    print("\n=== Prompt Examples ===")
    print(generate_prompt_examples())
