"""
LLM model loading and inference with HuggingFace transformers.
Provides lazy initialization and efficient model management.
"""
import logging
from typing import Optional, Iterator
from pathlib import Path

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)
from threading import Thread

from app.config import settings
from app.llm.config import LLMConfig

logger = logging.getLogger(__name__)


class LLMLoader:
    """
    Manages LLM model loading and inference with HuggingFace transformers.
    Uses lazy initialization - model is only loaded when first needed.
    Supports 4-bit quantization for efficient inference on consumer GPUs.
    """

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize the loader with configuration.

        Args:
            config: LLM configuration (uses app settings if not provided)
        """
        self.config = config or self._load_config_from_settings()
        self._model: Optional[AutoModelForCausalLM] = None
        self._tokenizer: Optional[AutoTokenizer] = None
        self._model_loaded = False

    @staticmethod
    def _load_config_from_settings() -> LLMConfig:
        """Load LLM config from application settings."""
        return LLMConfig(
            model_path=settings.model_path,
            context_size=settings.model_context_size,
            threads=settings.model_threads,
            temperature=settings.model_temperature,
        )

    def _load_model(self):
        """
        Load the model from HuggingFace or local path.
        Called automatically on first inference request.

        Returns:
            Tuple of (model, tokenizer)

        Raises:
            ValueError: If model path is not configured
        """
        if not self.config.model_path:
            raise ValueError(
                "Model path not configured. Set MODEL_PATH in .env file or pass to LLMConfig"
            )

        model_id = self.config.model_path
        logger.info(f"Loading model: {model_id}")
        logger.info(f"Context size: {self.config.context_size}")

        try:
            # Check if we have a GPU available
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")

            # Configure 4-bit quantization if using GPU (saves VRAM)
            quantization_config = None
            if device == "cuda":
                logger.info("Configuring 4-bit quantization for GPU")
                quantization_config = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=torch.float16,
                    bnb_4bit_use_double_quant=True,
                    bnb_4bit_quant_type="nf4",
                )

            # Load tokenizer
            logger.info("Loading tokenizer...")
            tokenizer = AutoTokenizer.from_pretrained(
                model_id,
                trust_remote_code=True,  # Phi-3 requires this
            )

            # Ensure tokenizer has pad token
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            # Load model
            logger.info("Loading model weights...")
            model = AutoModelForCausalLM.from_pretrained(
                model_id,
                quantization_config=quantization_config,
                device_map="auto" if device == "cuda" else None,
                trust_remote_code=True,  # Phi-3 requires this
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                attn_implementation="eager",  # Fix for Phi-3 cache compatibility issue
            )

            # Move to device if CPU
            if device == "cpu":
                model = model.to(device)

            self._model = model
            self._tokenizer = tokenizer
            self._model_loaded = True

            logger.info("Model loaded successfully")
            logger.info(f"Model size: ~{model.num_parameters() / 1e9:.2f}B parameters")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    @property
    def model(self) -> AutoModelForCausalLM:
        """
        Get the loaded model, loading it if necessary (lazy loading).

        Returns:
            Loaded model instance
        """
        if self._model is None:
            self._load_model()
        return self._model

    @property
    def tokenizer(self) -> AutoTokenizer:
        """
        Get the loaded tokenizer, loading it if necessary (lazy loading).

        Returns:
            Loaded tokenizer instance
        """
        if self._tokenizer is None:
            self._load_model()
        return self._tokenizer

    @property
    def is_loaded(self) -> bool:
        """Check if model is currently loaded."""
        return self._model_loaded

    def generate(
        self,
        prompt: str,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repeat_penalty: Optional[float] = None,
        stream: bool = False,
    ) -> str | Iterator[str]:
        """
        Generate text from a prompt.

        Args:
            prompt: Input prompt text
            max_tokens: Maximum tokens to generate (uses config default if not provided)
            temperature: Sampling temperature (uses config default if not provided)
            top_p: Nucleus sampling probability
            top_k: Top-k sampling
            repeat_penalty: Repetition penalty
            stream: If True, return an iterator for streaming generation

        Returns:
            Generated text (string if stream=False, iterator if stream=True)
        """
        # Use config defaults if not specified
        max_tokens = max_tokens or self.config.max_tokens
        temperature = temperature if temperature is not None else self.config.temperature
        top_p = top_p if top_p is not None else self.config.top_p
        top_k = top_k if top_k is not None else self.config.top_k
        repeat_penalty = repeat_penalty if repeat_penalty is not None else self.config.repeat_penalty

        logger.debug(f"Generating with max_tokens={max_tokens}, temperature={temperature}")

        try:
            # Tokenize input
            inputs = self.tokenizer(prompt, return_tensors="pt", padding=True)
            inputs = inputs.to(self.model.device)

            # Prepare generation config
            generation_kwargs = {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "repetition_penalty": repeat_penalty,
                "do_sample": temperature > 0,  # Use sampling if temp > 0
                "pad_token_id": self.tokenizer.pad_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "use_cache": True,  # Enable KV cache for fast generation
            }

            if stream:
                # Set up streaming
                streamer = TextIteratorStreamer(
                    self.tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True,
                )
                generation_kwargs["streamer"] = streamer

                # Run generation in separate thread
                thread = Thread(
                    target=self.model.generate,
                    kwargs={**inputs, **generation_kwargs},
                )
                thread.start()

                # Return iterator
                return streamer
            else:
                # Generate complete text
                with torch.no_grad():
                    output_ids = self.model.generate(
                        **inputs,
                        **generation_kwargs,
                    )

                # Decode output (skip prompt tokens)
                generated_ids = output_ids[0][inputs["input_ids"].shape[1]:]
                generated_text = self.tokenizer.decode(
                    generated_ids,
                    skip_special_tokens=True,
                )

                return generated_text

        except Exception as e:
            logger.error(f"Generation failed: {e}")
            raise

    def unload(self):
        """
        Unload the model from memory.
        Useful for freeing resources when model is not needed.
        """
        if self._model is not None:
            logger.info("Unloading model from memory")
            del self._model
            del self._tokenizer
            self._model = None
            self._tokenizer = None
            self._model_loaded = False

            # Clear CUDA cache if using GPU
            if torch.cuda.is_available():
                torch.cuda.empty_cache()


# Global model loader instance (lazy initialization)
_global_loader: Optional[LLMLoader] = None


def get_loader() -> LLMLoader:
    """
    Get the global LLM loader instance.
    Creates it if it doesn't exist (singleton pattern).

    Returns:
        Global LLMLoader instance
    """
    global _global_loader
    if _global_loader is None:
        _global_loader = LLMLoader()
    return _global_loader
