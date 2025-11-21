"""
LLM inference via OpenAI-compatible API.
Drop-in replacement for local model loader during testing/development.
"""
import logging
from typing import Optional, Iterator, List, Dict
from openai import OpenAI

from app.config import settings
from app.llm.config import LLMConfig

logger = logging.getLogger(__name__)


class APILoader:
    """
    Manages LLM inference via OpenAI API.
    Provides same interface as LLMLoader for easy switching.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize API loader with configuration.

        Args:
            config: LLM configuration (uses app settings if not provided)
        """
        self.config = config or self._load_config_from_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model_name = settings.openai_model
        self._model_loaded = True  # API is always "loaded"

        logger.info(f"Initialized OpenAI API client")
        logger.info(f"Model: {self.model_name}")

    @staticmethod
    def _load_config_from_settings() -> LLMConfig:
        """Load LLM config from application settings."""
        return LLMConfig(
            model_path=settings.openai_model,  # Use model name as "path"
            context_size=settings.model_context_size,
            threads=settings.model_threads,
            temperature=settings.model_temperature,
        )

    @property
    def model(self):
        """
        Dummy property for compatibility with LLMLoader interface.
        API doesn't expose model object directly.
        """
        return None

    @property
    def tokenizer(self):
        """
        Dummy tokenizer for compatibility.
        API handles tokenization internally.
        """
        # Return a simple mock with apply_chat_template method
        class MockTokenizer:
            def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
                """
                Mock chat template - OpenAI API handles this internally.
                Just return a simple text representation for prompt building.
                """
                result = []
                for msg in messages:
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    result.append(f"{role}: {content}")
                return "\n".join(result)

        return MockTokenizer()

    @property
    def is_loaded(self) -> bool:
        """Check if model is loaded (always True for API)."""
        return self._model_loaded

    def generate(
        self,
        prompt: str | List[Dict[str, str]],
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """
        Generate text via OpenAI API.

        Args:
            prompt: Input prompt (string or list of message dicts for OpenAI format)
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling probability
            top_k: Top-k sampling (ignored - OpenAI doesn't support)
            repeat_penalty: Repetition penalty (ignored - OpenAI doesn't support)
            stream: If True, return iterator for streaming

        Returns:
            Generated text (string if stream=False, iterator if stream=True)
        """
        # Use config defaults if not specified
        # For API mode, use higher token limit since speed isn't an issue (1024 vs 256 for local)
        max_tokens = max_tokens or 1024  # Higher default for API (not limited by local inference speed)
        temperature = temperature if temperature is not None else self.config.temperature
        top_p = top_p if top_p is not None else self.config.top_p

        logger.debug(f"Generating with max_tokens={max_tokens}, temperature={temperature}")

        try:
            # Convert prompt to messages format
            # OpenAI expects messages, not raw prompt
            # If prompt is already a list of messages (from build_prompt_with_memory without tokenizer), use directly
            if isinstance(prompt, list):
                messages = prompt
            else:
                # Legacy: wrap string prompt as user message
                messages = [{"role": "user", "content": prompt}]

            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                stream=stream,
            )

            if stream:
                # Return streaming iterator
                def stream_generator():
                    for chunk in response:
                        if chunk.choices[0].delta.content:
                            yield chunk.choices[0].delta.content

                return stream_generator()
            else:
                # Return complete text
                return response.choices[0].message.content

        except Exception as e:
            logger.error(f"API generation failed: {e}")
            raise

    def unload(self):
        """
        Unload the model (no-op for API).
        Included for interface compatibility.
        """
        logger.info("API loader unload called (no-op)")
        self._model_loaded = False


# Global API loader instance (lazy initialization)
_global_api_loader: Optional[APILoader] = None


def get_api_loader() -> APILoader:
    """
    Get the global API loader instance.
    Creates it if it doesn't exist (singleton pattern).

    Returns:
        Global APILoader instance
    """
    global _global_api_loader
    if _global_api_loader is None:
        _global_api_loader = APILoader()
    return _global_api_loader
