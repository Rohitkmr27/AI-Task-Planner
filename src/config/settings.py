"""
Application configuration via Pydantic Settings.

Loads configuration from environment variables and .env files.
Provides validated, typed settings for the entire application.

Usage:
    from src.config.settings import get_settings
    settings = get_settings()
    print(settings.gemini_model)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Resolve the project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env", override=True)


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables / .env file.

    Attributes are grouped by concern:
    - API keys (secrets)
    - Model configuration
    - Safety limits
    - File access controls
    - Database paths
    """

    model_config = SettingsConfigDict(
        env_file=(str(_PROJECT_ROOT / ".env"), str(_PROJECT_ROOT / ".env.example")),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # API Keys
    # ------------------------------------------------------------------ #
    google_api_key: SecretStr = Field(
        default=SecretStr(""),
        description="Google Gemini API key from https://aistudio.google.com/apikey",
    )
    serpapi_api_key: Optional[str] = Field(
        default=None,
        description="SerpAPI key for web search. If empty, mock results are used.",
    )

    # ------------------------------------------------------------------ #
    # Gemini Model
    # ------------------------------------------------------------------ #
    gemini_model: str = Field(
        default="gemini-1.5-flash",
        description="Gemini model name (gemini-1.5-flash or gemini-1.5-pro).",
    )
    gemini_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for Gemini responses.",
    )

    # ------------------------------------------------------------------ #
    # Safety Limits
    # ------------------------------------------------------------------ #
    max_code_exec_timeout: int = Field(
        default=10,
        ge=1,
        le=60,
        description="Max seconds for code execution subprocess.",
    )
    max_steps_per_run: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum execution steps per agent run.",
    )
    max_tokens_per_run: int = Field(
        default=50000,
        ge=1000,
        description="Maximum total tokens per agent run.",
    )
    max_retries_per_step: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts for a failed tool step.",
    )

    # ------------------------------------------------------------------ #
    # File Access
    # ------------------------------------------------------------------ #
    allowed_file_read_dirs: str = Field(
        default="./data,./",
        description="Comma-separated directories the file reader may access.",
    )
    email_draft_only: bool = Field(
        default=True,
        description="If True, email tool drafts only — never sends.",
    )

    # ------------------------------------------------------------------ #
    # Database
    # ------------------------------------------------------------------ #
    database_path: str = Field(
        default=str(_PROJECT_ROOT / "data" / "execution_logs.db"),
        description="Path to the SQLite execution log database.",
    )

    # ------------------------------------------------------------------ #
    # Dataset (read-only source)
    # ------------------------------------------------------------------ #
    dataset_path: str = Field(
        default=str(_PROJECT_ROOT / "dataset.csv"),
        description="Path to the original dataset.csv (read-only).",
    )

    # ------------------------------------------------------------------ #
    # Derived Properties
    # ------------------------------------------------------------------ #
    @property
    def allowed_dirs_list(self) -> list[Path]:
        """Parse comma-separated dir string into resolved Path objects."""
        dirs = []
        for d in self.allowed_file_read_dirs.split(","):
            d = d.strip()
            if d:
                resolved = (_PROJECT_ROOT / d).resolve()
                dirs.append(resolved)
        return dirs

    @property
    def has_google_api_key(self) -> bool:
        """Check if a non-empty Google API key is configured."""
        val = self.google_api_key.get_secret_value()
        return bool(val) and val != "your-gemini-api-key-here"

    @property
    def has_serpapi_key(self) -> bool:
        """Check if a SerpAPI key is configured."""
        return bool(self.serpapi_api_key)

    @property
    def project_root(self) -> Path:
        """Return the project root directory."""
        return _PROJECT_ROOT

    # ------------------------------------------------------------------ #
    # Validators
    # ------------------------------------------------------------------ #
    @field_validator("gemini_model")
    @classmethod
    def validate_model_name(cls, v: str) -> str:
        allowed = {
            "gemini-1.5-flash", "gemini-1.5-pro",
            "gemini-2.0-flash", "gemini-2.0-pro",
            "gemini-1.5-flash-latest", "gemini-1.5-pro-latest",
        }
        if v not in allowed:
            raise ValueError(
                f"Unknown Gemini model '{v}'. Allowed: {sorted(allowed)}"
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get the cached application settings singleton.

    Returns a cached Settings instance so that .env is only
    parsed once per process.
    """
    return Settings()


def require_google_api_key() -> str:
    """
    Return the Google API key or raise a clear error.

    Use this at agent startup to fail fast if the key is missing.
    """
    settings = get_settings()
    if not settings.has_google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not configured.\n"
            "1. Copy .env.example to .env\n"
            "2. Set your Gemini API key from https://aistudio.google.com/apikey\n"
        )
    return settings.google_api_key.get_secret_value()
