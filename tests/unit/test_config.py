"""
OpsSwarm — Test Suite: Core Config
=====================================
Unit tests for settings loading, computed fields, and validation.
"""

import os
import pytest
from pydantic import ValidationError


class TestAppSettings:
    """Tests for AppSettings Pydantic model."""

    def test_default_settings_load(self):
        """Settings load with defaults when no .env is present."""
        from core.config import AppSettings
        s = AppSettings()
        assert s.app_name == "OpsSwarm"
        assert s.app_env == "development"
        assert s.api_port == 8000

    def test_database_url_computed(self):
        """database_url is correctly assembled from components."""
        from core.config import AppSettings
        s = AppSettings(
            postgres_host="mydb",
            postgres_port=5432,
            postgres_user="user",
            postgres_password="pass",
            postgres_db="opsswarm",
        )
        assert s.database_url == "postgresql+asyncpg://user:pass@mydb:5432/opsswarm"

    def test_redis_url_no_password(self):
        """Redis URL omits password when empty."""
        from core.config import AppSettings
        s = AppSettings(redis_host="localhost", redis_port=6379, redis_password="")
        assert s.redis_url == "redis://localhost:6379/0"

    def test_redis_url_with_password(self):
        """Redis URL includes password when set."""
        from core.config import AppSettings
        s = AppSettings(redis_password="secret")
        assert ":secret@" in s.redis_url

    def test_secret_key_too_short_raises(self):
        """SECRET_KEY shorter than 32 chars raises ValidationError."""
        from core.config import AppSettings
        with pytest.raises(ValidationError):
            AppSettings(secret_key="short")

    def test_is_production_flag(self):
        """is_production returns True only for production env."""
        from core.config import AppSettings
        dev = AppSettings(app_env="development")
        prod = AppSettings(app_env="production")
        assert not dev.is_production
        assert prod.is_production

    def test_risk_threshold_bounds(self):
        """Risk score threshold must be between 0 and 10."""
        from core.config import AppSettings
        with pytest.raises(ValidationError):
            AppSettings(risk_score_approval_threshold=11.0)
        with pytest.raises(ValidationError):
            AppSettings(risk_score_approval_threshold=-1.0)
