"""
Display utilities using rich for terminal interface.
Provides beautiful formatting for messages, stats, and status.
"""
from typing import Dict, List, Any, AsyncIterator
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.status import Status
from rich.text import Text
from rich import box


# Global console instance
console = Console()


def display_welcome() -> None:
    """Show welcome banner with rich.Panel"""
    welcome_text = """
[bold green]Welcome to Eva Terminal Interface[/bold green]

A thoughtful companion who journals with you.
Type your message to chat, or use commands (type /help for list).

Ready to chat!
    """

    panel = Panel(
        welcome_text.strip(),
        title="Eva - Character Companion",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(panel)
    console.print()


def display_user_message(message: str) -> None:
    """Display user message in cyan"""
    console.print(f"[cyan]You:[/cyan] {message}")


def display_assistant_message(message: str) -> None:
    """Display Eva's message in green bold"""
    console.print(f"[bold green]Eva:[/bold green] {message}")


def display_system_message(message: str) -> None:
    """Display system message in yellow dim"""
    console.print(f"[dim yellow]{message}[/dim yellow]")


async def display_streaming_response(
    response_iterator: AsyncIterator[str],
    display_console: Console = None,
) -> str:
    """
    Display streaming response with rich.Live.
    Returns full response text.

    Handles special tags like <think>...</think> with custom formatting.

    Args:
        response_iterator: Async iterator yielding text chunks
        display_console: Console to use (defaults to global console)

    Returns:
        Complete response text
    """
    if display_console is None:
        display_console = console

    full_response = ""
    response_text = Text()
    response_text.append("Eva: ", style="bold green")

    with Live(response_text, console=display_console, refresh_per_second=10) as live:
        async for chunk in response_iterator:
            full_response += chunk
            # Update the display with formatted response
            new_text = Text()
            new_text.append("Eva: ", style="bold green")

            # Format response (handle <think> tags)
            formatted = _format_response_text(full_response)
            new_text.append(formatted)

            live.update(new_text)

    # Print newline after streaming completes
    display_console.print()

    return full_response


def _format_response_text(text: str) -> Text:
    """
    Format response text with special handling for thinking tags.

    Supports:
    - <think>...</think> (generic)
    - ###ponder###...###/ponder### (Qwen MOE)

    Args:
        text: Raw response text potentially containing special tags

    Returns:
        Rich Text object with formatted content
    """
    import re

    result = Text()

    # Pattern to find thinking blocks (both formats)
    # <think>...</think> OR ###ponder###...###/ponder###
    think_pattern = r'(<think>(.*?)</think>)|(###ponder###(.*?)###/ponder###)'

    last_end = 0
    for match in re.finditer(think_pattern, text, re.DOTALL):
        # Add text before the think block (normal text)
        if match.start() > last_end:
            result.append(text[last_end:match.start()])

        # Get think content (group 2 for <think>, group 4 for ###ponder###)
        think_content = (match.group(2) or match.group(4) or "").strip()

        # Add think block content in dim italic style
        result.append(f"[thinking: {think_content}]", style="dim italic")

        last_end = match.end()

    # Add remaining text after last think block
    if last_end < len(text):
        result.append(text[last_end:])

    return result


def display_stats_table(metadata: Dict[str, Any]) -> None:
    """Display conversation stats with rich.Table"""
    table = Table(
        title="Conversation Statistics",
        border_style="blue",
        box=box.ROUNDED,
    )

    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="green")

    # Add rows from metadata
    for key, value in metadata.items():
        # Format key (convert snake_case to Title Case)
        formatted_key = key.replace("_", " ").title()
        # Format value
        formatted_value = str(value)
        table.add_row(formatted_key, formatted_value)

    console.print(table)


def display_memories(memories: List[Dict[str, Any]]) -> None:
    """Display retrieved memories with formatting"""
    if not memories:
        display_system_message("No memories retrieved for this query.")
        return

    panel_content = []

    for i, memory in enumerate(memories, 1):
        # Extract memory details
        content = memory.get("content_summary", "")  # Fixed: retrieval returns 'content_summary'
        memory_type = memory.get("memory_type", "unknown")
        similarity = memory.get("similarity", 0.0)
        importance = memory.get("importance_score", 0.0)  # Fixed: retrieval returns 'importance_score'

        # Format memory entry
        memory_text = Text()
        memory_text.append(f"{i}. ", style="bold white")
        memory_text.append(f"[{memory_type}, ", style="dim cyan")
        memory_text.append(f"similarity: {similarity:.2f}, ", style="dim cyan")
        memory_text.append(f"importance: {importance:.2f}]", style="dim cyan")
        memory_text.append("\n   ")
        memory_text.append(f'"{content}"', style="white")

        panel_content.append(memory_text)

    # Combine all memory texts
    combined_text = Text("\n\n").join(panel_content)

    panel = Panel(
        combined_text,
        title=f"Retrieved Memories ({len(memories)})",
        border_style="magenta",
        box=box.ROUNDED,
    )

    console.print(panel)


def display_thinking() -> Status:
    """
    Return rich.Status for 'Eva is thinking...'.

    Usage:
        with display_thinking():
            # Do work
            pass
    """
    return console.status("[bold green]Eva is thinking...", spinner="dots")


def display_error(message: str) -> None:
    """Display error message in red"""
    console.print(f"[bold red]Error:[/bold red] {message}")


def display_command_help() -> None:
    """Display available commands in a formatted table"""
    table = Table(
        title="Available Commands",
        border_style="blue",
        box=box.ROUNDED,
    )

    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Description", style="white")

    commands = [
        ("/help", "Show this help message"),
        ("/exit or /quit", "Exit the terminal interface"),
        ("/restart", "Restart the terminal interface"),
        ("/stats", "Show conversation statistics"),
        ("/memories", "Show last retrieved memories"),
        ("/new", "Start a new conversation"),
        ("/clear", "Clear the terminal screen"),
        ("/mood", "Show Eva's current mood and state"),
        ("/history [n]", "Show recent conversation history (default: 10 turns)"),
        ("/debug [mode]", "Toggle debug output (memory|prompt|llm|all)"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


def clear_screen() -> None:
    """Clear the terminal screen"""
    console.clear()
