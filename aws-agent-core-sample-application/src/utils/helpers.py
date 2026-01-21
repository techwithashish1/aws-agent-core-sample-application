"""Utility functions for the application."""

import structlog
import logging
from typing import Any, Dict
import json


def setup_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """Set up structured logging.
    
    Args:
        log_level: Logging level
        log_format: Log format (json or console)
    """
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, log_level.upper())
    )

    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def format_tool_output(output: Any) -> str:
    """Format tool output for display.
    
    Args:
        output: Tool output
        
    Returns:
        Formatted string
    """
    if hasattr(output, 'dict'):
        return json.dumps(output.dict(), indent=2)
    elif isinstance(output, dict):
        return json.dumps(output, indent=2)
    return str(output)


def parse_aws_arn(arn: str) -> Dict[str, str]:
    """Parse an AWS ARN into components.
    
    Args:
        arn: AWS ARN string
        
    Returns:
        Dictionary of ARN components
    """
    parts = arn.split(":")
    
    if len(parts) < 6:
        return {"error": "Invalid ARN format"}
    
    return {
        "arn": parts[0],
        "partition": parts[1],
        "service": parts[2],
        "region": parts[3],
        "account_id": parts[4],
        "resource": ":".join(parts[5:])
    }


def validate_resource_name(name: str, resource_type: str) -> tuple[bool, str]:
    """Validate AWS resource name.
    
    Args:
        name: Resource name
        resource_type: Type of resource (s3, lambda, dynamodb)
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"
    
    if resource_type == "s3":
        # S3 bucket name rules
        if len(name) < 3 or len(name) > 63:
            return False, "S3 bucket name must be between 3 and 63 characters"
        if not name[0].isalnum() or not name[-1].isalnum():
            return False, "S3 bucket name must start and end with letter or number"
        if ".." in name or ".-" in name or "-." in name:
            return False, "Invalid character combination in S3 bucket name"
    
    elif resource_type == "lambda":
        # Lambda function name rules
        if len(name) > 64:
            return False, "Lambda function name cannot exceed 64 characters"
        if not all(c.isalnum() or c in "-_" for c in name):
            return False, "Lambda function name can only contain alphanumeric, hyphen, and underscore"
    
    elif resource_type == "dynamodb":
        # DynamoDB table name rules
        if len(name) < 3 or len(name) > 255:
            return False, "DynamoDB table name must be between 3 and 255 characters"
        if not all(c.isalnum() or c in "-._" for c in name):
            return False, "DynamoDB table name can only contain alphanumeric, hyphen, dot, and underscore"
    
    return True, ""
