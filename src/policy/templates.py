"""Cedar Policy Templates for AWS Resource Manager.

This module provides pre-built Cedar policy templates for common
access control scenarios in AWS resource management.

Cedar Policy Syntax Reference:
- permit/forbid: Allow or deny the action
- principal: Who can access (supports tags from JWT claims)
- action: What action they can perform (tool name)
- resource: What resource they can access (gateway ARN)
- when { conditions }: Under what conditions

Principal-based conditions:
- principal.hasTag("claim_name"): Check if claim exists
- principal.getTag("claim_name") == "value": Exact match
- principal.getTag("claim_name") like "*value*": Pattern match

Input-based conditions:
- context.input.field: Reference tool input parameters
- context.input.field == "value": Exact match
- context.input.field <= value: Numeric comparison
- context.input.field in ["a", "b"]: Set membership
"""

from typing import List, Optional


def get_region_restriction_policy(
    gateway_arn: str,
    action_name: str,
    allowed_regions: List[str],
    policy_name: Optional[str] = None
) -> dict:
    """Create a policy that restricts tool usage to specific AWS regions.
    
    Args:
        gateway_arn: ARN of the gateway.
        action_name: Name of the action/tool (e.g., "create_s3_bucket").
        allowed_regions: List of allowed AWS regions (e.g., ["ap-south-1", "us-east-1"]).
        policy_name: Optional custom policy name.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_region_restriction_policy(
        ...     gateway_arn="arn:aws:...",
        ...     action_name="create_s3_bucket",
        ...     allowed_regions=["ap-south-1", "eu-west-1"]
        ... )
    """
    regions_str = ", ".join(f'"{r}"' for r in allowed_regions)
    
    statement = (
        f'permit(principal, '
        f'action == AgentCore::Action::"{action_name}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ context.input.region in [{regions_str}] }};'
    )
    
    return {
        "name": policy_name or f"region_restriction_{action_name}",
        "description": f"Allow {action_name} only in regions: {', '.join(allowed_regions)}",
        "statement": statement
    }


def get_destructive_operation_policy(
    gateway_arn: str,
    action_name: str,
    blocked_patterns: List[str],
    field_name: str = "name",
    policy_name: Optional[str] = None
) -> dict:
    """Create a policy that blocks destructive operations on resources matching patterns.
    
    Args:
        gateway_arn: ARN of the gateway.
        action_name: Name of the delete action (e.g., "delete_s3_bucket").
        blocked_patterns: List of patterns to block (e.g., ["*prod*", "*important*"]).
        field_name: Input field containing the resource name (default: "name").
        policy_name: Optional custom policy name.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for forbid policy.
        
    Example:
        >>> policy = get_destructive_operation_policy(
        ...     gateway_arn="arn:aws:...",
        ...     action_name="delete_s3_bucket",
        ...     blocked_patterns=["*prod*", "*backup*"],
        ...     field_name="bucket_name"
        ... )
    """
    # Create OR conditions for each pattern
    conditions = " || ".join(
        f'context.input.{field_name} like "{pattern}"'
        for pattern in blocked_patterns
    )
    
    statement = (
        f'forbid(principal, '
        f'action == AgentCore::Action::"{action_name}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ {conditions} }};'
    )
    
    return {
        "name": policy_name or f"block_destructive_{action_name}",
        "description": f"Block {action_name} for resources matching: {', '.join(blocked_patterns)}",
        "statement": statement
    }


def get_role_based_policy(
    gateway_arn: str,
    action_names: List[str],
    required_role: str,
    policy_name: Optional[str] = None
) -> dict:
    """Create a policy that requires a specific role for certain actions.
    
    Args:
        gateway_arn: ARN of the gateway.
        action_names: List of action names that require the role.
        required_role: Role name required in principal's JWT claims.
        policy_name: Optional custom policy name.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_role_based_policy(
        ...     gateway_arn="arn:aws:...",
        ...     action_names=["delete_s3_bucket", "delete_lambda_function"],
        ...     required_role="admin"
        ... )
    """
    if len(action_names) == 1:
        action_clause = f'action == AgentCore::Action::"{action_names[0]}"'
    else:
        actions_str = ", ".join(f'AgentCore::Action::"{a}"' for a in action_names)
        action_clause = f'action in [{actions_str}]'
    
    statement = (
        f'permit(principal, '
        f'{action_clause}, '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ principal.hasTag("role") && principal.getTag("role") == "{required_role}" }};'
    )
    
    return {
        "name": policy_name or f"role_required_{required_role}",
        "description": f"Require '{required_role}' role for: {', '.join(action_names)}",
        "statement": statement
    }


def get_parameter_limit_policy(
    gateway_arn: str,
    action_name: str,
    field_name: str,
    max_value: int,
    policy_name: Optional[str] = None
) -> dict:
    """Create a policy that limits a numeric parameter to a maximum value.
    
    Args:
        gateway_arn: ARN of the gateway.
        action_name: Name of the action/tool.
        field_name: Input field to limit.
        max_value: Maximum allowed value.
        policy_name: Optional custom policy name.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_parameter_limit_policy(
        ...     gateway_arn="arn:aws:...",
        ...     action_name="create_lambda_function",
        ...     field_name="memory_size",
        ...     max_value=1024
        ... )
    """
    statement = (
        f'permit(principal, '
        f'action == AgentCore::Action::"{action_name}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ context.input.{field_name} <= {max_value} }};'
    )
    
    return {
        "name": policy_name or f"limit_{field_name}_{action_name}",
        "description": f"Limit {field_name} to max {max_value} for {action_name}",
        "statement": statement
    }


def get_allow_all_policy(
    gateway_arn: str,
    action_name: str = None,
    action_names: List[str] = None,
    policy_name: Optional[str] = None
) -> dict:
    """Create a policy that allows an action without restrictions.
    
    Use this to explicitly allow tools that should have no restrictions.
    Remember: When a Policy Engine is attached, default is DENY.
    
    Args:
        gateway_arn: ARN of the gateway.
        action_name: Optional - specific action to allow.
        action_names: Optional - list of actions to allow (for permit-all).
        policy_name: Optional custom policy name.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
    """
    if action_names:
        # Permit multiple specific actions
        actions_str = ", ".join(f'AgentCore::Action::"{a}"' for a in action_names)
        statement = (
            f'permit(principal, '
            f'action in [{actions_str}], '
            f'resource == AgentCore::Gateway::"{gateway_arn}");'
        )
        desc = f"Allow {len(action_names)} tools on this gateway"
        name = policy_name or "allow_all_tools"
    elif action_name:
        statement = (
            f'permit(principal, '
            f'action == AgentCore::Action::"{action_name}", '
            f'resource == AgentCore::Gateway::"{gateway_arn}");'
        )
        desc = f"Allow {action_name} without restrictions"
        name = policy_name or f"allow_{action_name}"
    else:
        # Fallback - permit all (may be rejected by AgentCore)
        statement = (
            f'permit(principal, '
            f'action, '
            f'resource == AgentCore::Gateway::"{gateway_arn}");'
        )
        desc = "Allow all tools on this gateway"
        name = policy_name or "allow_all_tools"
    
    return {
        "name": name,
        "description": desc,
        "statement": statement
    }


def get_combined_policy(
    gateway_arn: str,
    action_name: str,
    conditions: List[str],
    policy_name: Optional[str] = None,
    description: Optional[str] = None
) -> dict:
    """Create a policy with multiple combined conditions (AND).
    
    Args:
        gateway_arn: ARN of the gateway.
        action_name: Name of the action/tool.
        conditions: List of Cedar condition expressions.
        policy_name: Optional custom policy name.
        description: Optional policy description.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_combined_policy(
        ...     gateway_arn="arn:aws:...",
        ...     action_name="create_s3_bucket",
        ...     conditions=[
        ...         'context.input.region == "ap-south-1"',
        ...         'context.input.versioning_enabled == true',
        ...         'principal.hasTag("role")'
        ...     ]
        ... )
    """
    combined = " && ".join(f"({c})" for c in conditions)
    
    statement = (
        f'permit(principal, '
        f'action == AgentCore::Action::"{action_name}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ {combined} }};'
    )
    
    return {
        "name": policy_name or f"combined_{action_name}",
        "description": description or f"Combined conditions for {action_name}",
        "statement": statement
    }


# Pre-built policies for AWS Resource Manager tools
AWS_RESOURCE_MANAGER_POLICIES = {
    "s3": {
        "list_buckets": {
            "description": "Allow listing S3 buckets",
            "template": "allow_all"
        },
        "create_bucket_region_restricted": {
            "description": "Allow bucket creation only in approved regions",
            "template": "region_restriction",
            "config": {
                "action_name": "create_s3_bucket",
                "allowed_regions": ["ap-south-1", "us-east-1", "eu-west-1"]
            }
        },
        "block_prod_bucket_deletion": {
            "description": "Block deletion of production buckets",
            "template": "destructive_operation",
            "config": {
                "action_name": "delete_s3_bucket",
                "blocked_patterns": ["*prod*", "*production*", "*important*"],
                "field_name": "bucket_name"
            }
        }
    },
    "lambda": {
        "list_functions": {
            "description": "Allow listing Lambda functions",
            "template": "allow_all"
        },
        "limit_memory": {
            "description": "Limit Lambda memory to 1024MB",
            "template": "parameter_limit",
            "config": {
                "action_name": "create_lambda_function",
                "field_name": "memory_size",
                "max_value": 1024
            }
        },
        "admin_only_delete": {
            "description": "Only admins can delete Lambda functions",
            "template": "role_based",
            "config": {
                "action_names": ["delete_lambda_function"],
                "required_role": "admin"
            }
        }
    },
    "dynamodb": {
        "list_tables": {
            "description": "Allow listing DynamoDB tables",
            "template": "allow_all"
        },
        "admin_only_delete": {
            "description": "Only admins can delete DynamoDB tables",
            "template": "role_based",
            "config": {
                "action_names": ["delete_dynamodb_table"],
                "required_role": "admin"
            }
        }
    }
}
