"""
OpsSwarm — Centralised Configuration
=====================================
Loads all settings from environment variables (via .env file).
Uses Pydantic Settings for strict validation and type safety.

Usage:
    from core.config import settings
    print(settings.app_name)
    print(settings.database_url)
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────
    app_name: str = Field(default="OpsSwarm", description="Application name")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development"
    )
    app_version: str = Field(default="0.1.0")
    app_debug: bool = Field(default=False)
    app_log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO"
    )
    secret_key: str = Field(default="insecure-dev-secret-change-me")

    # ── API Server ───────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0")
    api_port: int = Field(default=8000, ge=1024, le=65535)
    api_workers: int = Field(default=1, ge=1)
    api_reload: bool = Field(default=True)

    # ── PostgreSQL ───────────────────────────────────────────
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="opsswarm")
    postgres_user: str = Field(default="opsswarm_user")
    postgres_password: str = Field(default="change-me")
    postgres_pool_size: int = Field(default=10, ge=1)
    postgres_max_overflow: int = Field(default=20, ge=0)

    @computed_field
    @property
    def database_url(self) -> str:
        """Async PostgreSQL connection URL."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field
    @property
    def database_url_sync(self) -> str:
        """Sync PostgreSQL connection URL (for Alembic migrations)."""
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # ── Redis ────────────────────────────────────────────────
    redis_host: str = Field(default="localhost")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)
    redis_max_connections: int = Field(default=20)

    @computed_field
    @property
    def redis_url(self) -> str:
        """Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # ── Qdrant ───────────────────────────────────────────────
    qdrant_host: str = Field(default="localhost")
    qdrant_port: int = Field(default=6333)
    qdrant_grpc_port: int = Field(default=6334)
    qdrant_api_key: str = Field(default="")
    qdrant_collection_runbooks: str = Field(default="runbooks")
    qdrant_collection_incidents: str = Field(default="historical_incidents")
    qdrant_collection_rca: str = Field(default="rca_knowledge_base")

    # ── LLM Providers ────────────────────────────────────────
    llm_provider: Literal["groq", "gemini", "openrouter", "ollama"] = Field(
        default="groq"
    )
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama3-70b-8192")

    gemini_api_key: str = Field(default="")
    gemini_model: str = Field(default="gemini-1.5-pro")

    openrouter_api_key: str = Field(default="")
    openrouter_model: str = Field(default="anthropic/claude-3-sonnet")

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3")

    # ── Embeddings ───────────────────────────────────────────
    embedding_provider: Literal["gemini", "openai", "ollama"] = Field(
        default="gemini"
    )
    embedding_model: str = Field(default="models/embedding-001")
    embedding_dimension: int = Field(default=768)
    openai_api_key: str = Field(default="")

    # ── AWS ──────────────────────────────────────────────────
    aws_region: str = Field(default="us-east-1")
    aws_access_key_id: str = Field(default="")
    aws_secret_access_key: str = Field(default="")
    aws_account_id: str = Field(default="")

    # S3
    s3_bucket_artifacts: str = Field(default="opsswarm-artifacts-dev")
    s3_bucket_reports: str = Field(default="opsswarm-reports-dev")

    # DynamoDB
    dynamodb_table_workflow_state: str = Field(
        default="opsswarm-workflow-state-dev"
    )
    dynamodb_table_agent_memory: str = Field(
        default="opsswarm-agent-memory-dev"
    )
    dynamodb_table_incident_lifecycle: str = Field(
        default="opsswarm-incident-lifecycle-dev"
    )

    # SQS
    sqs_queue_alert_ingest: str = Field(default="")
    sqs_queue_agent_tasks: str = Field(default="")
    sqs_queue_approval_requests: str = Field(default="")
    sqs_queue_remediation_results: str = Field(default="")

    # ── LangFuse ─────────────────────────────────────────────
    langfuse_public_key: str = Field(default="")
    langfuse_secret_key: str = Field(default="")
    langfuse_host: str = Field(default="https://cloud.langfuse.com")
    langfuse_enabled: bool = Field(default=False)

    # ── Safety & Guardrails ───────────────────────────────────
    risk_score_approval_threshold: float = Field(default=6.0, ge=0.0, le=10.0)
    max_auto_remediation_actions: int = Field(default=3, ge=1)
    human_approval_timeout_seconds: int = Field(default=300, ge=30)

    # ── Simulation ────────────────────────────────────────────
    simulation_data_path: str = Field(default="./data")
    simulation_seed: int = Field(default=42)
    simulation_incidents_count: int = Field(default=5, ge=1)

    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v: str, info) -> str:
        """Warn if default insecure key is used in production."""
        # We can't access other fields easily in validators,
        # so production check happens at app startup in main.py
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long.")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """
    Returns a cached singleton settings instance.
    Use this everywhere instead of creating a new AppSettings().

    Example:
        from core.config import get_settings
        settings = get_settings()
    """
    return AppSettings()


# Convenience singleton — import directly for most use cases
settings = get_settings()
