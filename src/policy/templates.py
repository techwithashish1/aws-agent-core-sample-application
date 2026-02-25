"""Cedar Policy Templates for AWS Resource Manager.

This module provides pre-built Cedar policy templates for common
access control scenarios in AWS resource management.

Cedar Policy Syntax Reference:
- permit/forbid: Allow or deny the action
- principal: Who can access (supports tags from JWT claims)
- action: What action they can perform (target___tool format)
- resource: What resource they can access (gateway ARN)
- when { conditions }: Under what conditions

Action Naming Convention:
- Gateway tool actions follow the format: <target-name>___<tool-name> (triple underscore)
- Example: resource-metrics-iam-target___Get_All_S3_Metrics

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


def build_action_name(target_name: str, tool_name: str = None) -> str:
    """Build the Cedar action name using triple underscore convention.
    
    Args:
        target_name: Name of the gateway target (e.g., "resource-metrics-iam-target")
        tool_name: Name of the specific tool (e.g., "Get_All_S3_Metrics")
        
    Returns:
        Formatted action name like "resource-metrics-iam-target___Get_All_S3_Metrics"
        or just target_name if tool_name is None
    """
    if tool_name:
        return f"{target_name}___{tool_name}"
    return target_name


def get_region_restriction_policy(
    gateway_arn: str,
    target_name: str,
    allowed_regions: List[str],
    tool_name: Optional[str] = None,
    policy_name: Optional[str] = None,
    action_name: Optional[str] = None,  # Deprecated, use target_name
) -> dict:
    """Create a policy that restricts tool usage to specific AWS regions.
    
    Args:
        gateway_arn: ARN of the gateway.
        target_name: Name of the gateway target (e.g., "resource-metrics-iam-target").
        allowed_regions: List of allowed AWS regions (e.g., ["ap-south-1", "us-east-1"]).
        tool_name: Optional tool name to restrict (for tool-specific policies).
        policy_name: Optional custom policy name.
        action_name: Deprecated - use target_name instead.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_region_restriction_policy(
        ...     gateway_arn="arn:aws:...",
        ...     target_name="my-iam-target",
        ...     tool_name="create_s3_bucket",
        ...     allowed_regions=["ap-south-1", "eu-west-1"]
        ... )
    """
    # Support legacy action_name parameter
    target = target_name or action_name
    regions_str = ", ".join(f'"{r}"' for r in allowed_regions)
    
    # Build action name using triple underscore convention
    action = build_action_name(target, tool_name)
    
    statement = (
        f'permit(principal, '
        f'action == AgentCore::Action::"{action}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ context.input.region in [{regions_str}] }};'
    )
    
    name_suffix = tool_name or target
    # Sanitize name to match regex ^[A-Za-z][A-Za-z0-9_]*$
    safe_name_suffix = name_suffix.replace("-", "_")
    return {
        "name": policy_name or f"region_restriction_{safe_name_suffix}",
        "description": f"Allow {name_suffix} only in regions: {', '.join(allowed_regions)}",
        "statement": statement
    }


def get_destructive_operation_policy(
    gateway_arn: str,
    target_name: str,
    blocked_patterns: List[str],
    field_name: str = "name",
    tool_name: Optional[str] = None,
    policy_name: Optional[str] = None,
    action_name: Optional[str] = None,  # Deprecated, use target_name
) -> dict:
    """Create a policy that blocks destructive operations on resources matching patterns.
    
    Args:
        gateway_arn: ARN of the gateway.
        target_name: Name of the gateway target (e.g., "my-iam-target").
        blocked_patterns: List of patterns to block (e.g., ["*prod*", "*important*"]).
        field_name: Input field containing the resource name (default: "name").
        tool_name: Optional tool name to match specific operations.
        policy_name: Optional custom policy name.
        action_name: Deprecated - use target_name instead.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for forbid policy.
        
    Example:
        >>> policy = get_destructive_operation_policy(
        ...     gateway_arn="arn:aws:...",
        ...     target_name="my-iam-target",
        ...     tool_name="delete_s3_bucket",
        ...     blocked_patterns=["*prod*", "*backup*"],
        ...     field_name="bucket_name"
        ... )
    """
    # Support legacy action_name parameter
    target = target_name or action_name
    
    # Build action name using triple underscore convention
    action = build_action_name(target, tool_name)
    
    # Create OR conditions for each pattern
    pattern_conditions = " || ".join(
        f'context.input.{field_name} like "{pattern}"'
        for pattern in blocked_patterns
    )
    
    statement = (
        f'forbid(principal, '
        f'action == AgentCore::Action::"{action}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ {pattern_conditions} }};'
    )
    
    name_suffix = tool_name or target
    # Sanitize name to match regex ^[A-Za-z][A-Za-z0-9_]*$
    safe_name_suffix = name_suffix.replace("-", "_")
    return {
        "name": policy_name or f"block_destructive_{safe_name_suffix}",
        "description": f"Block {name_suffix} for resources matching: {', '.join(blocked_patterns)}",
        "statement": statement
    }


def get_role_based_policy(
    gateway_arn: str,
    target_names: List[str],
    required_role: str,
    tool_names: Optional[List[str]] = None,
    policy_name: Optional[str] = None,
    action_names: Optional[List[str]] = None,  # Deprecated, use target_names
) -> dict:
    """Create a policy that requires a specific role for certain actions.
    
    Args:
        gateway_arn: ARN of the gateway.
        target_names: List of target names that require the role.
        required_role: Role name required in principal's JWT claims.
        tool_names: Optional list of tool names to combine with targets.
        policy_name: Optional custom policy name.
        action_names: Deprecated - use target_names instead.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_role_based_policy(
        ...     gateway_arn="arn:aws:...",
        ...     target_names=["my-iam-target"],
        ...     tool_names=["delete_s3_bucket"],
        ...     required_role="admin"
        ... )
    """
    # Support legacy action_names parameter
    targets = target_names or action_names or []
    
    # Build action names using triple underscore convention
    if tool_names and len(targets) == 1:
        # Create specific action for each tool
        actions = [build_action_name(targets[0], tool) for tool in tool_names]
    else:
        # Use targets as-is
        actions = targets
    
    if len(actions) == 1:
        action_clause = f'action == AgentCore::Action::"{actions[0]}"'
    else:
        actions_str = ", ".join(f'AgentCore::Action::"{a}"' for a in actions)
        action_clause = f'action in [{actions_str}]'
    
    # Build conditions - just role check
    statement = (
        f'permit(principal, '
        f'{action_clause}, '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ principal.hasTag("role") && principal.getTag("role") == "{required_role}" }};'
    )
    
    # Sanitize name
    safe_role = required_role.replace("-", "_")
    return {
        "name": policy_name or f"role_required_{safe_role}",
        "description": f"Require '{required_role}' role for: {', '.join(tool_names or targets)}",
        "statement": statement
    }


def get_parameter_limit_policy(
    gateway_arn: str,
    target_name: str,
    field_name: str,
    max_value: int,
    tool_name: Optional[str] = None,
    policy_name: Optional[str] = None,
    action_name: Optional[str] = None,  # Deprecated, use target_name
) -> dict:
    """Create a policy that limits a numeric parameter to a maximum value.
    
    Args:
        gateway_arn: ARN of the gateway.
        target_name: Name of the gateway target.
        field_name: Input field to limit.
        max_value: Maximum allowed value.
        tool_name: Optional tool name to combine with target.
        policy_name: Optional custom policy name.
        action_name: Deprecated - use target_name instead.
        
    Returns:
        Dict with 'name', 'description', and 'statement' for the policy.
        
    Example:
        >>> policy = get_parameter_limit_policy(
        ...     gateway_arn="arn:aws:...",
        ...     target_name="my-iam-target",
        ...     tool_name="create_lambda_function",
        ...     field_name="memory_size",
        ...     max_value=1024
        ... )
    """
    # Support legacy action_name parameter
    target = target_name or action_name
    
    # Build action name using triple underscore convention
    action = build_action_name(target, tool_name)
    
    statement = (
        f'permit(principal, '
        f'action == AgentCore::Action::"{action}", '
        f'resource == AgentCore::Gateway::"{gateway_arn}") '
        f'when {{ context.input.{field_name} <= {max_value} }};'
    )
    
    name_suffix = tool_name or target
    # Sanitize name to match regex ^[A-Za-z][A-Za-z0-9_]*$
    safe_name_suffix = name_suffix.replace("-", "_")
    safe_field_name = field_name.replace("-", "_")
    return {
        "name": policy_name or f"limit_{safe_field_name}_{safe_name_suffix}",
        "description": f"Limit {field_name} to max {max_value} for {name_suffix}",
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
# NOTE: These require target_name to be injected from gateway_config.json at runtime
# Action format: <target-name>___<tool-name> (triple underscore)
#
# IMPORTANT: Simple "allow all" policies are rejected as "overly permissive" by AgentCore.
# All policies must have conditions.
#
# Actual tools in the gateway target (resource-metrics-iam-target):
# - Get_All_S3_Metrics
# - Get_All_DynamoDB_Metrics
# - Get_All_Lambda_Metrics
# - Get_S3_Bucket_Metrics
# - Get_DynamoDB_Table_Metrics
# - Get_Lambda_Function_Metrics
AWS_RESOURCE_MANAGER_POLICIES = {
    "s3": {
        "admin_only_s3_metrics": {
            "description": "Only admins can view S3 bucket metrics",
            "template": "role_based",
            "config": {
                "tool_names": ["Get_All_S3_Metrics", "Get_S3_Bucket_Metrics"],
                "required_role": "admin"
            }
        }
    },
    "lambda": {
        "admin_only_lambda_metrics": {
            "description": "Only admins can view Lambda function metrics",
            "template": "role_based",
            "config": {
                "tool_names": ["Get_All_Lambda_Metrics", "Get_Lambda_Function_Metrics"],
                "required_role": "admin"
            }
        }
    },
    "dynamodb": {
        "admin_only_dynamodb_metrics": {
            "description": "Only admins can view DynamoDB table metrics",
            "template": "role_based",
            "config": {
                "tool_names": ["Get_All_DynamoDB_Metrics", "Get_DynamoDB_Table_Metrics"],
                "required_role": "admin"
            }
        }
    }
}
