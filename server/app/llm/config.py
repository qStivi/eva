"""
LLM configuration and settings.
"""
from typing import Optional
from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """Configuration for LLM model."""

    model_path: Optional[str] = Field(
        default=None,
        description="Path to GGUF model file"
    )
    context_size: int = Field(
        default=4096,
        description="Maximum context window size"
    )
    threads: int = Field(
        default=8,
        description="Number of threads for inference"
    )
    temperature: float = Field(
        default=0.5,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.5 optimized for Qwen MOE)"
    )
    max_tokens: int = Field(
        default=200,
        description="Maximum tokens to generate (reduced from 256 for faster responses)"
    )
    top_p: float = Field(
        default=0.95,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability (0.95 recommended for Qwen MOE)"
    )
    top_k: int = Field(
        default=40,
        description="Top-k sampling (40 recommended for Qwen MOE)"
    )
    repeat_penalty: float = Field(
        default=1.08,
        ge=1.0,
        description="Repetition penalty (1.08 for Qwen MOE thinking control)"
    )

    class Config:
        frozen = True  # Make immutable
