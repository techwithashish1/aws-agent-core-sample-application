"""AgentCore Policy Setup Script for AWS Resource Manager.

This script provides CLI commands to create and manage policy engines
and Cedar policies for the AWS Resource Manager agent.

Usage:
    # Create policy engine
    python -m policy.setup_policy --create-engine
    
    # Create policy engine and attach to gateway
    python -m policy.setup_policy --create-engine --gateway-id <gateway-id> --mode ENFORCE
    
    # List policy engines
    python -m policy.setup_policy --list-engines
    
    # Add a policy from natural language
    python -m policy.setup_policy --generate-policy "Allow bucket creation only in ap-south-1"
    
    # Add pre-built policies for AWS Resource Manager
    python -m policy.setup_policy --add-preset s3
    
    # Clean up policy engine
    python -m policy.setup_policy --cleanup --engine-id <engine-id>
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import boto3

from policy.client import PolicyManager
from policy.templates import (
    get_region_restriction_policy,
    get_destructive_operation_policy,
    get_role_based_policy,
    get_parameter_limit_policy,
    get_allow_all_policy,
    AWS_RESOURCE_MANAGER_POLICIES,
)
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("agentcore-policy")


def load_gateway_config() -> Optional[dict]:
    """Load gateway configuration from file."""
    config_path = Path(__file__).parent.parent / "agentcore_gateway" / "gateway_config.json"
    
    if not config_path.exists():
        return None
    
    with open(config_path) as f:
        return json.load(f)


def get_gateway_arn(gateway_config: dict) -> str:
    """Construct the full gateway ARN from config."""
    region = gateway_config.get('region', 'ap-south-1')
    gateway_id = gateway_config.get('gateway', {}).get('id')
    
    # Get account ID from the IAM role ARN
    iam_arn = gateway_config.get('iam_role', {}).get('arn', '')
    account_id = iam_arn.split(':')[4] if ':' in iam_arn else None
    
    if not gateway_id or not account_id:
        raise ValueError("Could not determine gateway ID or account ID from config")
    
    return f"arn:aws:bedrock-agentcore:{region}:{account_id}:gateway/{gateway_id}"


def save_policy_config(config: dict) -> None:
    """Save policy configuration to file."""
    config_path = Path(__file__).parent.parent / "agentcore_gateway" / "policy_config.json"
    
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    print(f"\nConfiguration saved to: {config_path}")


def create_engine(args):
    """Create a policy engine and optionally attach to gateway."""
    manager = PolicyManager(region_name=args.region)
    
    print("\n" + "=" * 60)
    print("Creating Policy Engine")
    print("=" * 60)
    
    engine = manager.create_policy_engine(
        name=args.name,
        description=args.description
    )
    
    print(f"\n✅ Policy Engine Created:")
    print(f"   ID: {engine['policyEngineId']}")
    print(f"   ARN: {engine['policyEngineArn']}")
    
    config = {
        "policy_engine_id": engine['policyEngineId'],
        "policy_engine_arn": engine['policyEngineArn'],
        "region": args.region
    }
    
    # Attach to gateway if specified
    if args.gateway_id:
        print(f"\n🔗 Attaching to gateway: {args.gateway_id}")
        manager.attach_to_gateway(
            gateway_id=args.gateway_id,
            mode=args.mode
        )
        print(f"   Mode: {args.mode}")
        config["gateway_id"] = args.gateway_id
        config["mode"] = args.mode
    
    save_policy_config(config)
    
    print("\n" + "=" * 60)
    print("⚠️  IMPORTANT: When Policy Engine is attached in ENFORCE mode,")
    print("    ALL tool access is DENIED by default. You must create")
    print("    policies to PERMIT specific actions.")
    print("=" * 60)
    
    return engine


def list_engines(args):
    """List all policy engines."""
    manager = PolicyManager(region_name=args.region)
    
    print("\n" + "=" * 60)
    print("Policy Engines")
    print("=" * 60)
    
    engines = manager.list_policy_engines()
    
    if not engines:
        print("\nNo policy engines found.")
        return
    
    for engine in engines:
        print(f"\nID: {engine.get('policyEngineId', 'N/A')}")
        print(f"Name: {engine.get('name', 'N/A')}")
        print(f"Status: {engine.get('status', 'N/A')}")
        print("-" * 40)


def add_policy(args):
    """Add a single Cedar policy."""
    manager = PolicyManager(region_name=args.region)
    
    if not args.engine_id:
        print("Error: --engine-id is required")
        sys.exit(1)
    
    manager.policy_engine_id = args.engine_id
    
    print("\n" + "=" * 60)
    print(f"Creating Policy: {args.policy_name}")
    print("=" * 60)
    
    policy = manager.create_policy(
        name=args.policy_name,
        cedar_statement=args.cedar,
        description=args.policy_description
    )
    
    print(f"\n✅ Policy Created:")
    print(f"   ID: {policy['policyId']}")
    print(f"   Name: {args.policy_name}")
    print(f"   Statement: {args.cedar[:100]}...")


def generate_policy(args):
    """Generate policy from natural language."""
    manager = PolicyManager(region_name=args.region)
    
    gateway_config = load_gateway_config()
    if not gateway_config:
        print("Error: gateway_config.json not found. Run gateway setup first.")
        sys.exit(1)
    
    try:
        gateway_arn = get_gateway_arn(gateway_config)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("Generating Policy from Natural Language")
    print("=" * 60)
    print(f"\nInput: {args.nl_statement}")
    
    policies = manager.generate_policy_from_nl(
        natural_language=args.nl_statement,
        gateway_arn=gateway_arn
    )
    
    print(f"\n✅ Generated {len(policies)} policy/policies:\n")
    
    for i, policy in enumerate(policies, 1):
        print(f"--- Policy {i} ---")
        print(policy.get('statement', 'N/A'))
        print()
    
    if args.create and args.engine_id:
        manager.policy_engine_id = args.engine_id
        for i, policy in enumerate(policies, 1):
            created = manager.create_policy(
                name=f"generated_policy_{i}",
                cedar_statement=policy['statement'],
                description=f"Generated from: {args.nl_statement[:50]}..."
            )
            print(f"✅ Created policy: {created['policyId']}")


def add_preset_policies(args):
    """Add preset policies for AWS Resource Manager tools."""
    manager = PolicyManager(region_name=args.region)
    
    if not args.engine_id:
        print("Error: --engine-id is required")
        sys.exit(1)
    
    gateway_config = load_gateway_config()
    if not gateway_config:
        print("Error: gateway_config.json not found. Run gateway setup first.")
        sys.exit(1)
    
    try:
        gateway_arn = get_gateway_arn(gateway_config)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
        
    manager.policy_engine_id = args.engine_id
    
    preset = args.add_preset.lower()
    
    print("\n" + "=" * 60)
    print(f"Adding Preset Policies: {preset}")
    print("=" * 60)
    
    if preset == "all":
        services = list(AWS_RESOURCE_MANAGER_POLICIES.keys())
    elif preset in AWS_RESOURCE_MANAGER_POLICIES:
        services = [preset]
    else:
        print(f"Error: Unknown preset '{preset}'. Available: s3, lambda, dynamodb, all")
        sys.exit(1)
    
    created_count = 0
    
    for service in services:
        policies = AWS_RESOURCE_MANAGER_POLICIES.get(service, {})
        print(f"\n📦 {service.upper()} Policies:")
        
        for policy_name, policy_config in policies.items():
            template = policy_config.get('template')
            config = policy_config.get('config', {})
            
            # Generate the policy statement based on template
            if template == 'allow_all':
                action = config.get('action_name', f"list_{service}")
                policy_def = get_allow_all_policy(gateway_arn, action)
            elif template == 'region_restriction':
                policy_def = get_region_restriction_policy(gateway_arn, **config)
            elif template == 'destructive_operation':
                policy_def = get_destructive_operation_policy(gateway_arn, **config)
            elif template == 'role_based':
                policy_def = get_role_based_policy(gateway_arn, **config)
            elif template == 'parameter_limit':
                policy_def = get_parameter_limit_policy(gateway_arn, **config)
            else:
                continue
            
            try:
                created = manager.create_policy(
                    name=policy_def['name'],
                    cedar_statement=policy_def['statement'],
                    description=policy_def['description']
                )
                print(f"   ✅ {policy_def['name']}: {policy_config['description']}")
                created_count += 1
            except Exception as e:
                print(f"   ❌ {policy_def['name']}: {e}")
    
    print(f"\n✅ Created {created_count} policies")


def list_policies(args):
    """List policies in a policy engine."""
    manager = PolicyManager(region_name=args.region)
    
    if not args.engine_id:
        print("Error: --engine-id is required")
        sys.exit(1)
    
    manager.policy_engine_id = args.engine_id
    
    print("\n" + "=" * 60)
    print(f"Policies in Engine: {args.engine_id}")
    print("=" * 60)
    
    policies = manager.list_policies()
    
    if not policies:
        print("\nNo policies found.")
        return
    
    for policy in policies:
        # Handle both dict and string responses
        if isinstance(policy, dict):
            print(f"\nID: {policy.get('policyId', 'N/A')}")
            print(f"Name: {policy.get('name', 'N/A')}")
            print(f"Status: {policy.get('status', 'N/A')}")
        else:
            print(f"\nPolicy: {policy}")
        print("-" * 40)


def fix_gateway_role(args):
    """Fix the gateway role trust policy for policy engine attachment."""
    if not args.role_name:
        print("Error: --role-name is required")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print(f"Fixing Gateway Role Trust Policy: {args.role_name}")
    print("=" * 60)
    
    # Get account ID
    sts = boto3.client('sts')
    account_id = sts.get_caller_identity()['Account']
    
    # Updated trust policy with wildcard region
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "AssumeRolePolicy",
                "Effect": "Allow",
                "Principal": {
                    "Service": "bedrock-agentcore.amazonaws.com"
                },
                "Action": "sts:AssumeRole",
                "Condition": {
                    "StringEquals": {
                        "aws:SourceAccount": account_id
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:*:{account_id}:*"
                    }
                }
            }
        ]
    }
    
    iam = boto3.client('iam')
    
    try:
        iam.update_assume_role_policy(
            RoleName=args.role_name,
            PolicyDocument=json.dumps(trust_policy)
        )
        print(f"\n✅ Trust policy updated successfully!")
        print(f"   Role: {args.role_name}")
        print(f"   Account: {account_id}")
        print(f"   Regions: ALL (*)")
        print("\n   The gateway role can now be used with policy engines in any region.")
    except iam.exceptions.NoSuchEntityException:
        print(f"\n❌ Error: Role '{args.role_name}' not found")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error updating trust policy: {e}")
        sys.exit(1)


def cleanup(args):
    """Clean up policy engine and all its policies."""
    manager = PolicyManager(region_name=args.region)
    
    if not args.engine_id:
        print("Error: --engine-id is required")
        sys.exit(1)
    
    manager.policy_engine_id = args.engine_id
    
    print("\n" + "=" * 60)
    print(f"Cleaning Up Policy Engine: {args.engine_id}")
    print("=" * 60)
    
    # Detach from gateway first if specified
    if args.gateway_id:
        print(f"\n🔗 Detaching from gateway: {args.gateway_id}")
        manager.detach_from_gateway(args.gateway_id)
    
    print("\n🧹 Deleting policies and engine...")
    manager.cleanup()
    
    print("\n✅ Cleanup complete!")


def permit_all(args):
    """Create a simple policy that permits all tools on the gateway."""
    import os
    from pathlib import Path
    
    # Import here to avoid circular imports
    try:
        from gateway_integration.mcp_client import MCPGatewayClient
        has_mcp_client = True
    except ImportError:
        has_mcp_client = False
    
    manager = PolicyManager(region_name=args.region)
    
    if not args.engine_id:
        print("Error: --engine-id is required")
        sys.exit(1)
    
    gateway_config = load_gateway_config()
    if not gateway_config:
        print("Error: gateway_config.json not found. Run gateway setup first.")
        sys.exit(1)
    
    try:
        gateway_arn = get_gateway_arn(gateway_config)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    manager.policy_engine_id = args.engine_id
    
    print("\n" + "=" * 60)
    print("Creating Permit-All Policy")
    print("=" * 60)
    print(f"\nGateway ARN: {gateway_arn}")
    
    # Try to get actual tool names from gateway
    action_names = []
    
    if has_mcp_client:
        print("\n📋 Querying gateway for available tools...")
        try:
            # Temporarily disable SSL verification for corporate environments
            old_ssl = os.environ.get('SSL_VERIFY', 'true')
            os.environ['SSL_VERIFY'] = 'false'
            
            config_path = Path(__file__).parent.parent / "agentcore_gateway" / "gateway_config.json"
            client = MCPGatewayClient.from_config(str(config_path))
            
            if client.initialize():
                tools = client.list_tools()
                action_names = [tool.name for tool in tools]
                print(f"\n   Found {len(action_names)} tools:")
                for name in action_names:
                    print(f"   - {name}")
            
            os.environ['SSL_VERIFY'] = old_ssl
        except Exception as e:
            print(f"\n⚠️  Could not query gateway tools: {e}")
    
    if not action_names:
        print("\n⚠️  Could not get tools from gateway.")
        print("   Please specify tool names manually or check gateway configuration.")
        print("\n   You can list tools using the MCP client:")
        print("   python -c \"from gateway_integration.mcp_client import MCPGatewayClient; ...\"")
        sys.exit(1)
    
    # Get the policy definition with explicit actions
    policy_def = get_allow_all_policy(gateway_arn, action_names=action_names)
    
    print(f"\nCedar Statement:\n{policy_def['statement']}")
    
    # Check if policy already exists
    existing_policies = manager.list_policies()
    for existing in existing_policies:
        if existing.get('name') == policy_def['name']:
            print(f"\n⚠️  Policy '{policy_def['name']}' already exists!")
            print(f"   ID: {existing['policyId']}")
            print(f"   Status: {existing['status']}")
            print(f"\n   Skipping creation. Use --cleanup to remove and recreate.")
            return
    
    try:
        created = manager.create_policy(
            name=policy_def['name'],
            cedar_statement=policy_def['statement'],
            description=policy_def['description']
        )
        print(f"\n✅ Policy Created:")
        print(f"   ID: {created['policyId']}")
        print(f"   Name: {policy_def['name']}")
        print(f"   Tools: {len(action_names)}")
        print(f"\n   All {len(action_names)} gateway tools are now permitted!")
    except Exception as e:
        print(f"\n❌ Failed to create policy: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="AgentCore Policy Setup for AWS Resource Manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create policy engine and attach to gateway
  python -m policy.setup_policy --create-engine --gateway-id gw-123 --mode ENFORCE

  # List all policy engines
  python -m policy.setup_policy --list-engines

  # Add preset policies for S3 tools
  python -m policy.setup_policy --add-preset s3 --engine-id pe-123

  # Generate policy from natural language
  python -m policy.setup_policy --generate-policy "Block deletion of production buckets" --engine-id pe-123 --create

  # List policies in an engine
  python -m policy.setup_policy --list-policies --engine-id pe-123

  # Clean up
  python -m policy.setup_policy --cleanup --engine-id pe-123 --gateway-id gw-123

  # Fix gateway role trust policy (required before attaching policy engine)
  python -m policy.setup_policy --fix-gateway-role --role-name agentcore-my-gateway-role

  # Permit all tools (simple policy to allow everything)
  python -m policy.setup_policy --permit-all --engine-id pe-123
        """
    )
    
    parser.add_argument("--region", default=settings.aws_region,
                        help=f"AWS region (default: {settings.aws_region})")
    
    # Actions
    parser.add_argument("--create-engine", action="store_true",
                        help="Create a new policy engine")
    parser.add_argument("--list-engines", action="store_true",
                        help="List all policy engines")
    parser.add_argument("--add-policy", action="store_true",
                        help="Add a Cedar policy")
    parser.add_argument("--generate-policy", metavar="NL_STATEMENT",
                        help="Generate policy from natural language")
    parser.add_argument("--add-preset", metavar="PRESET",
                        help="Add preset policies (s3, lambda, dynamodb, all)")
    parser.add_argument("--permit-all", action="store_true",
                        help="Create a single policy to permit ALL tools (use after attaching engine)")
    parser.add_argument("--list-policies", action="store_true",
                        help="List policies in an engine")
    parser.add_argument("--cleanup", action="store_true",
                        help="Clean up policy engine")
    parser.add_argument("--fix-gateway-role", action="store_true",
                        help="Fix gateway role trust policy for policy engine attachment")
    
    # Options
    parser.add_argument("--role-name", metavar="NAME",
                        help="Gateway role name (for --fix-gateway-role)")
    parser.add_argument("--engine-id", metavar="ID",
                        help="Policy engine ID")
    parser.add_argument("--gateway-id", metavar="ID",
                        help="Gateway ID to attach/detach")
    parser.add_argument("--mode", choices=["ENFORCE", "LOG_ONLY"], default="ENFORCE",
                        help="Policy enforcement mode (default: ENFORCE)")
    parser.add_argument("--name", metavar="NAME",
                        help="Name for the policy engine")
    parser.add_argument("--description", metavar="DESC",
                        help="Description for the policy engine")
    parser.add_argument("--policy-name", metavar="NAME",
                        help="Name for the policy")
    parser.add_argument("--policy-description", metavar="DESC",
                        help="Description for the policy")
    parser.add_argument("--cedar", metavar="STATEMENT",
                        help="Cedar policy statement")
    parser.add_argument("--create", action="store_true",
                        help="Create generated policies in the engine")
    
    args = parser.parse_args()
    
    # Execute the appropriate action
    if args.create_engine:
        create_engine(args)
    elif args.list_engines:
        list_engines(args)
    elif args.add_policy:
        add_policy(args)
    elif args.generate_policy:
        generate_policy(args)
    elif args.add_preset:
        add_preset_policies(args)
    elif args.permit_all:
        permit_all(args)
    elif args.list_policies:
        list_policies(args)
    elif args.cleanup:
        cleanup(args)
    elif args.fix_gateway_role:
        fix_gateway_role(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
