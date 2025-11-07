"""
LLM generation endpoint for testing and simple interactions.
"""
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.llm.loader import get_loader
from app.llm.prompts import PromptManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["generation"])


class GenerateRequest(BaseModel):
    """Request model for text generation."""

    prompt: str = Field(
        ...,
        description="Input prompt for generation",
        min_length=1,
        max_length=4000,
    )
    max_tokens: Optional[int] = Field(
        default=None,
        description="Maximum tokens to generate (uses model default if not specified)",
        ge=1,
        le=2048,
    )
    temperature: Optional[float] = Field(
        default=None,
        description="Sampling temperature (uses model default if not specified)",
        ge=0.0,
        le=2.0,
    )
    use_character: bool = Field(
        default=False,
        description="If True, wrap prompt with Eva's character context",
    )


class GenerateResponse(BaseModel):
    """Response model for text generation."""

    text: str = Field(..., description="Generated text")
    prompt_tokens: int = Field(..., description="Approximate number of tokens in prompt")
    generated_tokens: int = Field(..., description="Approximate number of tokens generated")
    time_seconds: float = Field(..., description="Time taken to generate")
    model_loaded: bool = Field(..., description="Whether model was already loaded")


@router.post("/generate", response_model=GenerateResponse)
async def generate_text(request: GenerateRequest) -> GenerateResponse:
    """
    Generate text from a prompt using the LLM.

    This is a simple endpoint for testing and quick interactions.
    For full character conversations, use the WebSocket endpoint.

    Args:
        request: Generation request with prompt and parameters

    Returns:
        Generated text with metadata

    Raises:
        HTTPException: If generation fails
    """
    try:
        loader = get_loader()
        was_loaded = loader.is_loaded

        # Optionally wrap with character context
        if request.use_character:
            prompt = PromptManager.create_simple_prompt(request.prompt)
            logger.info("Using character prompt wrapper")
        else:
            prompt = request.prompt

        # Track generation time
        start_time = time.time()

        # Generate
        logger.info(f"Generating response (max_tokens={request.max_tokens})")
        generated_text = loader.generate(
            prompt=prompt,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
        )

        end_time = time.time()
        generation_time = end_time - start_time

        # Approximate token counts (rough estimate: 4 chars per token)
        prompt_tokens = len(prompt) // 4
        generated_tokens = len(generated_text) // 4

        logger.info(
            f"Generation complete in {generation_time:.2f}s "
            f"({generated_tokens} tokens, {generated_tokens/generation_time:.1f} tokens/s)"
        )

        return GenerateResponse(
            text=generated_text,
            prompt_tokens=prompt_tokens,
            generated_tokens=generated_tokens,
            time_seconds=round(generation_time, 2),
            model_loaded=was_loaded,
        )

    except FileNotFoundError as e:
        logger.error(f"Model file not found: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model not configured or not found. Check MODEL_PATH in .env file. Error: {str(e)}",
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Model configuration error: {str(e)}",
        )
    except Exception as e:
        logger.error(f"Generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Text generation failed: {str(e)}",
        )


@router.get("/model/status")
async def get_model_status():
    """
    Get current model loading status.

    Returns:
        Model status information
    """
    try:
        loader = get_loader()
        return {
            "loaded": loader.is_loaded,
            "model_path": loader.config.model_path,
            "context_size": loader.config.context_size,
            "temperature": loader.config.temperature,
        }
    except Exception as e:
        return {
            "loaded": False,
            "error": str(e),
        }
