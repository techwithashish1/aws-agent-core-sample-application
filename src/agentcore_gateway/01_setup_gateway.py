"""
Step 01: Setup AgentCore Gateway (IAM Role + Cognito + Gateway)

This script performs the initial AgentCore Gateway setup:
1. Creates IAM Role for AgentCore Gateway
2. Configures Cognito for JWT-based inbound authentication
3. Creates the AgentCore Gateway with MCP protocol

Usage:
    python 01_setup_gateway.py
"""

import os
import sys
import json
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file (check src/.env first, then local)
src_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
local_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
load_dotenv(src_env)
load_dotenv(local_env, override=True)  # Local overrides if exists

# Add src directory to path for config import (must be first)
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from config import settings

# Import utils from current directory explicitly to avoid conflicts
import importlib.util
utils_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'utils.py')
spec = importlib.util.spec_from_file_location("gateway_utils", utils_path)
utils = importlib.util.module_from_spec(spec)
spec.loader.exec_module(utils)

# Configuration - use settings.aws_region as default
REGION = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', settings.aws_region))
GATEWAY_NAME = "resource-metrics-ac-gateway"
USER_POOL_NAME = "resource-metrics-gateway-pool"
RESOURCE_SERVER_ID = "resource-metrics-gateway-id"
RESOURCE_SERVER_NAME = "resource-metrics-gateway-name"
CLIENT_NAME = "resource-metrics-gateway-client"
SCOPES = [
    {
        "ScopeName": "invoke",
        "ScopeDescription": "Scope for invoking the agentcore gateway"
    }
]


def setup_iam_role(config):
    """Step 1: Create IAM Role for AgentCore Gateway."""
    print("=" * 70)
    print("Part 1: Create IAM Role for AgentCore Gateway")
    print("=" * 70)
    print(f"Region: {REGION}")
    print(f"Gateway Name: {GATEWAY_NAME}")
    
    print("Creating IAM Role for AgentCore Gateway...")
    agentcore_gateway_iam_role = utils.create_agentcore_gateway_role(GATEWAY_NAME, region=REGION)
    
    role_arn = agentcore_gateway_iam_role['Role']['Arn']
    role_name = agentcore_gateway_iam_role['Role']['RoleName']
    
    print("IAM Role created successfully!")
    print(f"Role Name: {role_name}")
    print(f"Role ARN: {role_arn}")
    
    config["region"] = REGION
    config["gateway_name"] = GATEWAY_NAME
    config["iam_role"] = {
        "arn": role_arn,
        "name": role_name
    }
    
    return config


def setup_cognito(config):
    """Step 2: Configure Cognito for inbound authentication."""
    print("=" * 70)
    print("Part 2: Configure Amazon Cognito for Inbound Authentication")
    print("=" * 70)
    print(f"User Pool Name: {USER_POOL_NAME}")
    print(f"Resource Server ID: {RESOURCE_SERVER_ID}")
    print(f"Client Name: {CLIENT_NAME}")
    
    # Build scope names
    scope_names = [f"{RESOURCE_SERVER_ID}/{scope['ScopeName']}" for scope in SCOPES]
    scope_string = " ".join(scope_names)
    
    # Create Cognito client
    cognito = boto3.client("cognito-idp", region_name=REGION)
    
    print("Creating or retrieving Cognito resources...")
    
    # Create/Get User Pool
    print("1. Setting up User Pool...")
    user_pool_id = utils.get_or_create_user_pool(cognito, USER_POOL_NAME)
    print(f"User Pool ID: {user_pool_id}")
    
    # Create/Get Resource Server
    print("2. Setting up Resource Server...")
    utils.get_or_create_resource_server(
        cognito, 
        user_pool_id, 
        RESOURCE_SERVER_ID, 
        RESOURCE_SERVER_NAME, 
        SCOPES
    )
    print(f"Resource Server ID: {RESOURCE_SERVER_ID}")
    
    # Create/Get M2M Client
    print("3. Setting up M2M Client...")
    client_id, client_secret = utils.get_or_create_m2m_client(
        cognito, 
        user_pool_id, 
        CLIENT_NAME, 
        RESOURCE_SERVER_ID, 
        scope_names
    )
    print(f"Client ID: {client_id}")
    
    # Build discovery URL
    cognito_discovery_url = f'https://cognito-idp.{REGION}.amazonaws.com/{user_pool_id}/.well-known/openid-configuration'
    print(f"4. Discovery URL: {cognito_discovery_url}")
    
    config["cognito"] = {
        "user_pool_id": user_pool_id,
        "user_pool_name": USER_POOL_NAME,
        "resource_server_id": RESOURCE_SERVER_ID,
        "client_id": client_id,
        "client_secret": client_secret,
        "scope_names": scope_names,
        "scope_string": scope_string,
        "discovery_url": cognito_discovery_url
    }
    
    print("Cognito setup complete!")
    print(f"User Pool ID: {user_pool_id}")
    print(f"Client ID: {client_id}")
    print(f"Scopes: {scope_string}")
    
    return config


def create_gateway(config):
    """Step 3: Create the AgentCore Gateway."""
    print("=" * 70)
    print("Part 3: Create AgentCore Gateway")
    print("=" * 70)
    print(f"Gateway Name: {GATEWAY_NAME}")
    
    # Get values from config
    role_arn = config["iam_role"]["arn"]
    client_id = config["cognito"]["client_id"]
    discovery_url = config["cognito"]["discovery_url"]
    
    print(f"Using IAM Role: {role_arn}")
    print(f"Using Cognito Client ID: {client_id}")
    print(f"Using Discovery URL: {discovery_url}")
    
    # Create Gateway client
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    # Build auth configuration
    auth_config = {
        "customJWTAuthorizer": {
            "allowedClients": [client_id],
            "discoveryUrl": discovery_url
        }
    }
    
    print("Creating AgentCore Gateway...")
    
    try:
        create_response = gateway_client.create_gateway(
            name=GATEWAY_NAME,
            roleArn=role_arn,
            protocolType='MCP',
            protocolConfiguration={
                'mcp': {
                    'supportedVersions': ['2025-03-26'],
                    'searchType': 'SEMANTIC'
                }
            },
            authorizerType='CUSTOM_JWT',
            authorizerConfiguration=auth_config,
            description='AgentCore Gateway for Resource Metrics API'
        )
        
        gateway_id = create_response["gatewayId"]
        gateway_url = create_response["gatewayUrl"]
        
        print("Gateway created successfully!")
        print(f"Gateway ID: {gateway_id}")
        print(f"Gateway URL: {gateway_url}")
        
        config["gateway"] = {
            "id": gateway_id,
            "url": gateway_url,
            "name": GATEWAY_NAME
        }
        
    except gateway_client.exceptions.ConflictException:
        print("Gateway with this name already exists. Retrieving existing gateway...")
        
        list_response = gateway_client.list_gateways(maxResults=50)
        for gw in list_response.get('items', []):
            if gw['name'] == GATEWAY_NAME:
                gateway_id = gw['gatewayId']
                gateway_url = gw['gatewayUrl']
                print("Found existing gateway!")
                print(f"Gateway ID: {gateway_id}")
                print(f"Gateway URL: {gateway_url}")
                
                config["gateway"] = {
                    "id": gateway_id,
                    "url": gateway_url,
                    "name": GATEWAY_NAME
                }
                break
        else:
            print("Error: Could not find the existing gateway.")
            return None
    
    except Exception as e:
        print(f"Error creating gateway: {e}")
        return None
    
    return config


def main():
    print("=" * 70)
    print("AgentCore Gateway Setup - Step 1")
    print("IAM Role + Cognito + Gateway Creation")
    print("=" * 70)
    print(f"Region: {REGION}")
    
    config = {}
    
    # Part 1: Create IAM Role
    config = setup_iam_role(config)
    if not config:
        return None
    
    # Part 2: Setup Cognito
    config = setup_cognito(config)
    if not config:
        return None
    
    # Part 3: Create Gateway
    config = create_gateway(config)
    if not config:
        return None
    
    # Save configuration
    utils.save_config(config)
    
    print("=" * 70)
    print("Step 1 Complete - Gateway Setup Finished!")
    print("=" * 70)
    print(f"Gateway ID: {config['gateway']['id']}")
    print(f"Gateway URL: {config['gateway']['url']}")
    print(f"Cognito User Pool ID: {config['cognito']['user_pool_id']}")
    print(f"Cognito Client ID: {config['cognito']['client_id']}")
    print("Next step: Run 02_create_targets.py to create credential provider and gateway targets")
    
    return config


if __name__ == "__main__":
    main()
