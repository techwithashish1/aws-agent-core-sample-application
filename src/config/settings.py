"""Configuration settings for AWS Resource Manager."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = "ap-south-1"
    aws_account_id: Optional[str] = None

    # AWS Bedrock Configuration
    bedrock_model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0"
    bedrock_region: str = "ap-south-1"
    max_tokens: int = 4096
    temperature: float = 0.7

    # Agent Configuration
    agent_name: str = "aws-resource-manager"
    agent_description: str = "AI-powered AWS resource management agent"
    max_iterations: int = 10
    verbose: bool = True

    # MCP Configuration
    mcp_server_port: int = 3000
    mcp_log_level: str = "INFO"

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Resource Limits
    max_s3_buckets_per_request: int = 5
    max_lambda_functions_per_request: int = 5
    max_dynamodb_tables_per_request: int = 5

    # Security
    enable_audit_logging: bool = True
    require_approval_for_destructive_operations: bool = True

    # AgentCore Memory Configuration
    memory_enabled: bool = True
    memory_name: Optional[str] = None  # Defaults to agent_name-memory
    memory_id: Optional[str] = None  # Set after memory creation
    memory_event_expiry_days: int = 7
    memory_region: Optional[str] = None  # Defaults to aws_region

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


# Global settings instance
settings = Settings()
