"""
Configuration management using pydantic-settings.
Loads from environment variables and .env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # Application
    app_name: str = "Eva Character Companion"
    app_version: str = "0.1.0"
    debug: bool = Field(default=False, validation_alias="DEBUG")

    # Server
    host: str = Field(default="0.0.0.0", validation_alias="HOST")
    port: int = Field(default=8080, validation_alias="PORT")

    # Database URLs
    database_url: str = Field(
        default="postgresql://user:pass@localhost:5432/character_companion",
        validation_alias="DATABASE_URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379",
        validation_alias="REDIS_URL"
    )
    chroma_host: str = Field(default="localhost", validation_alias="CHROMA_HOST")
    chroma_port: int = Field(default=8000, validation_alias="CHROMA_PORT")

    # LLM Configuration
    use_api: bool = Field(default=False, validation_alias="USE_API")
    openai_api_key: Optional[str] = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")
    model_path: Optional[str] = Field(default=None, validation_alias="MODEL_PATH")
    model_context_size: int = Field(default=4096, validation_alias="MODEL_CONTEXT_SIZE")
    model_threads: int = Field(default=8, validation_alias="MODEL_THREADS")
    model_temperature: float = Field(default=0.7, validation_alias="MODEL_TEMPERATURE")

    # Character Configuration
    character_name: str = Field(default="Eva", validation_alias="CHARACTER_NAME")
    default_mood: str = Field(default="neutral", validation_alias="DEFAULT_MOOD")

    # Feature Flags
    voice_enabled: bool = Field(default=False, validation_alias="VOICE_ENABLED")
    journal_enabled: bool = Field(default=True, validation_alias="JOURNAL_ENABLED")

    # Optional Voice
    whisper_model: str = Field(default="base", validation_alias="WHISPER_MODEL")
    tts_enabled: bool = Field(default=False, validation_alias="TTS_ENABLED")

    # Security
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        validation_alias="SECRET_KEY"
    )

    # Logseq Integration
    logseq_directory: Optional[str] = Field(
        default=None,
        validation_alias="LOGSEQ_DIRECTORY"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()
