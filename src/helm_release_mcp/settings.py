"""Application settings using pydantic-settings."""

from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_prefix="HELM_MCP_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    github_token: str = Field(
        default="",
        description="GitHub Personal Access Token with repo scope",
    )

    # Optional with defaults
    workspace_dir: Path = Field(
        default=Path.home() / ".helm-release-mcp" / "workspace",
        description="Directory for cloning repositories",
    )

    config_path: Path = Field(
        default=Path("config/repos.yaml"),
        description="Path to repository configuration file",
    )

    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO",
        description="Logging level",
    )

    # GitHub API settings
    github_api_base_url: str = Field(
        default="https://api.github.com",
        description="GitHub API base URL (for GitHub Enterprise)",
    )

    auth_token: str | None = Field(
        default=None,
        description="Shared bearer token required for MCP HTTP requests",
    )

    auth_issuer_url: AnyHttpUrl | None = Field(
        default=None,
        description="OAuth issuer URL used for auth metadata",
    )

    auth_resource_url: AnyHttpUrl | None = Field(
        default=None,
        description="OAuth resource server URL used for auth metadata",
    )

    # Timeouts
    workflow_poll_interval: int = Field(
        default=10,
        description="Seconds between workflow status polls",
    )

    workflow_timeout: int = Field(
        default=3600,
        description="Default workflow wait timeout in seconds",
    )


# Global settings instance - lazy loaded
_settings: Settings | None = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    if not _settings.github_token:
        raise ValueError("HELM_MCP_GITHUB_TOKEN must be set")
    return _settings
