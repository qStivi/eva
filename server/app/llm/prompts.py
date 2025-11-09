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
    def build_prompt_with_memory(
        system_prompt: str,
        context: str,
        conversation_history: List[Dict[str, str]],
        tokenizer = None,
    ) -> str | List[Dict[str, str]]:
        """
        Build complete prompt with two-track memory integration.

        This is the main function for Phase 3's two-track architecture.
        It combines:
        - Track 1: Clean conversation history (what's actually said)
        - Track 2: Rich side context (injected separately)

        Args:
            system_prompt: Eva's character prompt
            context: Built context from ContextManager (Track 2)
            conversation_history: List of message dicts with 'role' and 'content' keys (Track 1)
            tokenizer: Optional tokenizer for chat template formatting (recommended for model compatibility)

        Returns:
            If tokenizer provided: Formatted prompt string using model's chat template
            If no tokenizer: List of message dicts for manual formatting

        Example:
            >>> history = [
            ...     {"role": "user", "content": "Hi Eva!"},
            ...     {"role": "assistant", "content": "Hey! How are you?"},
            ... ]
            >>> context = "User Preferences:\\n- User prefers to be called: Alice"
            >>> prompt = PromptManager.build_prompt_with_memory(
            ...     system_prompt=PromptManager.SYSTEM_PROMPT,
            ...     context=context,
            ...     conversation_history=history,
            ...     tokenizer=tokenizer,  # Use model's chat template
            ... )
        """
        # Build system content: character prompt + context (Track 2)
        system_content = system_prompt
        if context:
            system_content += f"\n\n{context}"

        # Build messages in chat format
        messages = [{"role": "system", "content": system_content}]

        # Add conversation history (Track 1)
        for msg in conversation_history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

        # Use tokenizer's chat template if available (recommended!)
        if tokenizer is not None:
            try:
                # Use model's built-in chat template (handles all special tokens correctly)
                prompt = tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,  # Return string, not tokens
                    add_generation_prompt=True,  # Add start token for assistant response
                )
                return prompt
            except Exception as e:
                # Fallback to messages if template fails
                import logging
                logging.warning(f"Failed to apply chat template: {e}, returning message list")
                return messages
        else:
            # Return messages for manual formatting (legacy path)
            return messages

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
