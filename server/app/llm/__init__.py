"""
LLM integration module for Eva character.
Handles model loading, inference, and prompt management.
"""

from app.llm.loader import LLMLoader
from app.llm.prompts import PromptManager

__all__ = ["LLMLoader", "PromptManager"]
