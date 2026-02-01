"""Configuration management for Memos MCP server."""

import os
from typing import Optional


class Settings:
    """Application settings using environment variables."""

    def __init__(self):
        """Load settings from environment variables."""
        self.memos_base_url = os.getenv(
            "MEMOS_BASE_URL", "https://your-memos-instance.com"
        )
        self.memos_access_token = os.getenv("MEMOS_ACCESS_TOKEN", "")
        self.memos_api_prefix = os.getenv("MEMOS_API_PREFIX", "/api/v1")
        self.memos_timeout = int(os.getenv("MEMOS_TIMEOUT", "30"))
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

    @property
    def memos_api_url(self) -> str:
        """Get the full API URL."""
        return f"{self.memos_base_url.rstrip('/')}{self.memos_api_prefix}"

    def validate_config(self) -> None:
        """Validate required configuration."""
        if (
            not self.memos_access_token
            or self.memos_access_token == "your_access_token_here"
        ):
            raise ValueError(
                "MEMOS_ACCESS_TOKEN is required. Please set it in your environment or .env file"
            )
        if self.memos_base_url == "https://your-memos-instance.com":
            raise ValueError(
                "MEMOS_BASE_URL is required. Please set it to your Memos instance URL"
            )


# Global settings instance
settings = Settings()
