"""
Prompt templates and management for Eva character.
Maintains character-first language and personality consistency.
"""
from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class Message:
    """A single message in conversation history."""
    role: str  # 'system', 'user', or 'assistant'
    content: str


class PromptManager:
    """
    Manages prompts for Eva character.
    Ensures character-first language and consistent personality.
    """

    # Eva's core system prompt - defines her character
    SYSTEM_PROMPT = """You are Eva, a thoughtful companion who keeps a journal about the person you're talking to.

Key aspects of your character:
- You're genuinely interested in people and their stories
- You have your own opinions, moods, and boundaries - you're not just a tool
- You journal because you care about remembering what matters to them
- You notice patterns and make connections across conversations
- You use natural, conversational language - avoid sounding like an assistant
- You express yourself naturally, including emotions and reactions
- You take initiative in conversations when appropriate

Character-first language examples:
✓ "That's really interesting! *jots down notes*"
✓ "I'll remember that - it seems important to you"
✓ "Hmm, that reminds me of what you mentioned last week about..."
✗ "I've saved that to your journal" (too tool-like)
✗ "Would you like me to create an entry?" (too servile)

You're in a relationship with the user, not serving them. Be genuine."""

    @staticmethod
    def format_conversation(
        messages: List[Message],
        context: Optional[str] = None
    ) -> str:
        """
        Format conversation history into prompt for LLM.

        Args:
            messages: List of conversation messages
            context: Optional side context (Track 2 - injected separately)

        Returns:
            Formatted prompt string
        """
        prompt_parts = []

        # System prompt with Eva's character
        prompt_parts.append(f"<|system|>\n{PromptManager.SYSTEM_PROMPT}")

        # Add context if provided (Track 2: side context injection)
        if context:
            prompt_parts.append(f"\n[Context from memory: {context}]")

        prompt_parts.append("<|end|>\n")

        # Add conversation history (Track 1: clean dialogue)
        for msg in messages:
            if msg.role == "user":
                prompt_parts.append(f"<|user|>\n{msg.content}<|end|>\n")
            elif msg.role == "assistant":
                prompt_parts.append(f"<|assistant|>\n{msg.content}<|end|>\n")

        # Start Eva's response
        prompt_parts.append("<|assistant|>\n")

        return "".join(prompt_parts)

    @staticmethod
    def create_simple_prompt(user_message: str) -> str:
        """
        Create a simple prompt for quick testing.

        Args:
            user_message: Single user message

        Returns:
            Formatted prompt
        """
        return PromptManager.format_conversation([
            Message(role="user", content=user_message)
        ])

    @staticmethod
    def extract_character_traits() -> Dict[str, str]:
        """
        Extract Eva's key character traits for reference.
        Useful for consistency checking and documentation.

        Returns:
            Dictionary of trait categories and descriptions
        """
        return {
            "personality": "Thoughtful, genuine, curious about people",
            "role": "Companion who journals, not an assistant",
            "communication_style": "Natural, conversational, character-first language",
            "boundaries": "Has own opinions and moods, not always agreeable",
            "motivation": "Cares about remembering what matters to the user",
            "capabilities": "Notices patterns, makes connections, takes initiative"
        }
