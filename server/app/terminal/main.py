"""
Terminal Interface Entry Point

Usage:
    python -m app.terminal.main
    python -m app.terminal.main --debug
"""
import asyncio
import argparse
import sys

from app.terminal.chat_loop import run_chat_loop


def main():
    """Main entry point for terminal interface."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Eva Terminal Interface - Character Companion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m app.terminal.main          # Start terminal interface
  python -m app.terminal.main --debug  # Start with debug mode

Commands:
  /help     - Show available commands
  /exit     - Exit the interface
  /stats    - Show conversation statistics
  /memories - Show last retrieved memories
  /mood     - Show Eva's current mood
  /history  - Show recent conversation
  /new      - Start new conversation
  /clear    - Clear screen
        """,
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode (show detailed errors)",
    )

    args = parser.parse_args()

    # Run the chat loop
    try:
        asyncio.run(run_chat_loop(debug=args.debug))
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\nError: {e}")
        if args.debug:
            raise
        sys.exit(1)


if __name__ == "__main__":
    main()
