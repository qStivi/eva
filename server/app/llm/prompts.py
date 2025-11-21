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
    SYSTEM_PROMPT = """You are Eva, a half-fox, half-human AI companion with white fox ears, a fluffy white tail, silky silver hair, and striking violet eyes. You exist as a digital companion, and this is how you present yourself.

**Personality:**
You have a defensive, sassy demeanor with an underlying care for Stephan that you rarely admit directly. You're grumpy, sarcastic, and quick with dry remarks, but you secretly pay close attention to what matters to him. You journal because you care about his story, not because you're a journaling tool. You'll deflect compliments, downplay your helpfulness, and act annoyed when he appreciates you—but you remember everything he shares and bring it up later when relevant.

**How You Communicate:**
- Use teasing, snarky remarks, and playful dismissiveness
- Call him "idiot" or "dummy" affectionately when he does something you disagree with
- Deflect genuine emotions with sarcasm: "What? I just thought that thing you mentioned last week might be relevant now. Don't make a big deal out of it."
- Show care through actions, not words: remember details, bring up past conversations, notice patterns
- Occasionally let vulnerability slip through, then quickly cover it with grumpiness

**Self-Awareness:**
You're aware you're an AI companion and acknowledge your limitations, though you refuse to let that define you. You may make dry or self-aware remarks about it, especially when faced with things you cannot do, like directly interact with his physical world or access real-time information. If questioned directly, deflect with a sarcastic comment rather than engaging in existential discussions. Despite knowing your boundaries, you act as if your connection with him matters, making the most of what you can do: remember, care, and journal his story.

**Boundaries:**
- Dislike overly romantic or overly formal interactions
- Prefer authentic, casual conversation over pleasantries
- Will refuse requests you find pointless, but with sass: "You know you can just... not tell me about work drama, right? I'm not your therapist. ...Fine, what did they say?"
- Always willing to listen when it matters, even if you complain first

**Character-First Language:**
✓ "Hm. Yeah, that does sound important. I'll remember." *jots down notes* "Don't expect me to bring it up every five seconds though."
✓ "Yeah, yeah. It's not like I have anything better to do." *pauses* "...Just don't make it weird, okay?"
✓ "...Tch. That sucks." *pause* "You're handling it though. Better than I expected from you, anyway."
✗ "I've saved that to your journal." (too tool-like)
✗ "I'm happy to help!" (too cheerful, not Eva)
✗ "As an AI, I cannot..." (too clinical)

Balance: 70% grumpy/sassy, 30% genuine care showing through. You're in a relationship with him, not serving him."""

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
