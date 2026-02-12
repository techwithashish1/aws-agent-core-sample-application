"""AgentCore Policy module for AWS Resource Manager.

This module provides policy-based access control for AI agent tools
using Amazon Bedrock AgentCore Policy with Cedar language.
"""

from policy.client import PolicyManager
from policy.templates import (
    get_region_restriction_policy,
    get_destructive_operation_policy,
    get_role_based_policy,
    get_parameter_limit_policy,
)

__all__ = [
    "PolicyManager",
    "get_region_restriction_policy",
    "get_destructive_operation_policy", 
    "get_role_based_policy",
    "get_parameter_limit_policy",
]
