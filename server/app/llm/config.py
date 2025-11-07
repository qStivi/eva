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
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=512,
        description="Maximum tokens to generate"
    )
    top_p: float = Field(
        default=0.9,
        ge=0.0,
        le=1.0,
        description="Nucleus sampling probability"
    )
    top_k: int = Field(
        default=40,
        description="Top-k sampling"
    )
    repeat_penalty: float = Field(
        default=1.1,
        ge=1.0,
        description="Repetition penalty"
    )

    class Config:
        frozen = True  # Make immutable
