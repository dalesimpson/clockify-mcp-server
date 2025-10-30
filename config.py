"""Configuration for Clockify MCP Server."""

import os
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ClockifyConfig:
    """Configuration settings for Clockify API."""

    def __init__(self):
        """Initialize configuration from environment variables."""
        self.api_key: Optional[str] = os.getenv("CLOCKIFY_API_KEY")
        self.workspace_id: Optional[str] = os.getenv("CLOCKIFY_WORKSPACE_ID")
        self.base_url: str = os.getenv(
            "CLOCKIFY_API_URL", "https://api.clockify.me/api/v1"
        )

    def validate(self) -> None:
        """Validate that required configuration is present."""
        if not self.api_key:
            raise ValueError(
                "CLOCKIFY_API_KEY environment variable is required. "
                "Get your API key from: https://app.clockify.me/user/settings"
            )
        if not self.workspace_id:
            raise ValueError(
                "CLOCKIFY_WORKSPACE_ID environment variable is required. "
                "Find your workspace ID in Clockify workspace settings."
            )

    @property
    def headers(self) -> dict[str, str]:
        """Get HTTP headers for API requests."""
        return {
            "X-Api-Key": self.api_key or "",
            "Content-Type": "application/json",
        }


# Global configuration instance
config = ClockifyConfig()
