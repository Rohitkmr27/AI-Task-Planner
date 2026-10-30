"""
Unit tests for the application configuration module (src.config.settings).
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config.settings import Settings, get_settings, require_google_api_key


class TestSettings:
    """Test suite for Pydantic BaseSettings loading and validation."""

    def test_default_settings(self):
        """Settings should load with sensible defaults."""
        settings = Settings(
            google_api_key="test-key",  # type: ignore
            _env_file=None,
        )
        assert settings.gemini_model == "gemini-1.5-flash"
        assert settings.gemini_temperature == 0.2
        assert settings.max_code_exec_timeout == 10
        assert settings.max_steps_per_run == 10
        assert settings.max_tokens_per_run == 50000
        assert settings.max_retries_per_step == 2
        assert settings.email_draft_only is True

    def test_secret_str_masking(self):
        """API key should not be exposed in raw string representations."""
        settings = Settings(
            google_api_key="my-super-secret-key-12345",  # type: ignore
            _env_file=None,
        )
        repr_str = repr(settings)
        str_str = str(settings)
        assert "my-super-secret-key-12345" not in repr_str
        assert "my-super-secret-key-12345" not in str_str
        assert settings.google_api_key.get_secret_value() == "my-super-secret-key-12345"

    def test_has_google_api_key_check(self):
        """has_google_api_key should return False for empty or placeholder keys."""
        s1 = Settings(google_api_key="", _env_file=None)  # type: ignore
        assert s1.has_google_api_key is False

        s2 = Settings(google_api_key="your-gemini-api-key-here", _env_file=None)  # type: ignore
        assert s2.has_google_api_key is False

        s3 = Settings(google_api_key="AIzaSyRealKey123", _env_file=None)  # type: ignore
        assert s3.has_google_api_key is True

    def test_gemini_model_validation(self):
        """Invalid model names should raise ValidationError."""
        with pytest.raises(ValidationError):
            Settings(gemini_model="gpt-4o", _env_file=None)  # type: ignore

        # Valid model names should pass
        s = Settings(gemini_model="gemini-1.5-pro", _env_file=None)  # type: ignore
        assert s.gemini_model == "gemini-1.5-pro"

    def test_temperature_validation(self):
        """Temperature must be between 0.0 and 2.0."""
        with pytest.raises(ValidationError):
            Settings(gemini_temperature=-0.5, _env_file=None)  # type: ignore

        with pytest.raises(ValidationError):
            Settings(gemini_temperature=2.5, _env_file=None)  # type: ignore

        s = Settings(gemini_temperature=0.7, _env_file=None)  # type: ignore
        assert s.gemini_temperature == 0.7

    def test_allowed_dirs_list_parsing(self):
        """Comma-separated directory strings should resolve to Path objects."""
        settings = Settings(
            allowed_file_read_dirs="./data, ./outputs, ./",
            _env_file=None,
        )
        dirs = settings.allowed_dirs_list
        assert len(dirs) == 3
        for d in dirs:
            assert isinstance(d, Path)
            assert d.is_absolute()

    def test_require_google_api_key_raises_when_missing(self):
        """require_google_api_key should raise RuntimeError when not set."""
        with patch("src.config.settings.get_settings") as mock_get:
            mock_settings = Settings(google_api_key="", _env_file=None)  # type: ignore
            mock_get.return_value = mock_settings
            with pytest.raises(RuntimeError, match="GOOGLE_API_KEY is not configured"):
                require_google_api_key()

    def test_require_google_api_key_returns_secret_when_present(self):
        """require_google_api_key returns raw key when valid."""
        with patch("src.config.settings.get_settings") as mock_get:
            mock_settings = Settings(google_api_key="valid-key-xyz", _env_file=None)  # type: ignore
            mock_get.return_value = mock_settings
            assert require_google_api_key() == "valid-key-xyz"
