"""
Step 02: Create Credential Provider and Gateway Targets

This script creates:
1. API Key Credential Provider for API Key-authorized endpoints
2. Gateway Target for IAM-authorized endpoints (S3, DynamoDB, Lambda metrics)
3. Gateway Target for API Key-authorized endpoints (Report endpoint)

Usage:
    python 02_create_targets.py
"""

import os
import sys
import boto3
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

# Add parent directory to path for utils import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import utils

# Configuration
REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
CREDENTIAL_PROVIDER_NAME = "resource-metrics-api-key-provider"
IAM_TARGET_NAME = "resource-metrics-iam-target"
APIKEY_TARGET_NAME = "resource-metrics-apikey-target"

# API Key and API ID from .env file
API_KEY = os.environ.get('RESOURCE_METRICS_API_KEY', '')
API_ID = os.environ.get('RESOURCE_METRICS_API_ID', '')


def create_credential_provider(config):
    """Part 1: Create API Key Credential Provider."""
    print("=" * 70)
    print("Part 1: Create API Key Credential Provider")
    print("=" * 70)
    print(f"Credential Provider Name: {CREDENTIAL_PROVIDER_NAME}")
    
    if not API_KEY:
        print("Error: API Key not provided.")
        print("Please set RESOURCE_METRICS_API_KEY in .env file.")
        return None
    
    print(f"API Key (first 8 chars): {API_KEY[:8]}...")
    
    bedrock_agent_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    print("Creating API Key Credential Provider...")
    
    try:
        credential_provider_response = bedrock_agent_client.create_api_key_credential_provider(
            name=CREDENTIAL_PROVIDER_NAME,
            apiKey=API_KEY,
            tags={
                'ProjectName': 'ResourceMetricsAPI',
                'Purpose': 'AgentCore-APIGW-Integration'
            }
        )
        
        secret_arn = credential_provider_response['apiKeySecretArn']['secretArn']
        credential_provider_arn = credential_provider_response['credentialProviderArn']
        
        print("Credential Provider created successfully!")
        print(f"Credential Provider ARN: {credential_provider_arn}")
        print(f"Secret ARN: {secret_arn}")
        
        config["credential_provider"] = {
            "name": CREDENTIAL_PROVIDER_NAME,
            "arn": credential_provider_arn,
            "secret_arn": secret_arn
        }
        
    except (bedrock_agent_client.exceptions.ConflictException, 
            bedrock_agent_client.exceptions.ValidationException) as e:
        # Handle both ConflictException and ValidationException for existing provider
        if "already exists" in str(e):
            print("Credential Provider already exists. Retrieving existing provider...")
            
            try:
                get_response = bedrock_agent_client.get_api_key_credential_provider(
                    name=CREDENTIAL_PROVIDER_NAME
                )
                credential_provider_arn = get_response['credentialProviderArn']
                
                print("Found existing credential provider!")
                print(f"Credential Provider ARN: {credential_provider_arn}")
                
                config["credential_provider"] = {
                    "name": CREDENTIAL_PROVIDER_NAME,
                    "arn": credential_provider_arn
                }
                
            except Exception as e2:
                print(f"Error retrieving existing credential provider: {e2}")
                return None
        else:
            print(f"Error creating credential provider: {e}")
            return None
    
    except Exception as e:
        print(f"Error creating credential provider: {e}")
        return None
    
    return config


def create_iam_target(config, gateway_client, gateway_id, api_id):
    """Part 2: Create Gateway Target for IAM-authorized endpoints."""
    print("=" * 70)
    print("Part 2: Create Gateway Target - IAM-Authorized Endpoints")
    print("=" * 70)
    print(f"Target Name: {IAM_TARGET_NAME}")
    print(f"Endpoints: /api/metrics/s3, /api/metrics/dynamodb, /api/metrics/lambda")
    
    print("Creating Gateway Target for IAM-authorized endpoints...")
    
    try:
        create_gateway_target_response = gateway_client.create_gateway_target(
            name=IAM_TARGET_NAME,
            gatewayIdentifier=gateway_id,
            targetConfiguration={
                "mcp": {
                    "apiGateway": {
                        "restApiId": api_id,
                        "stage": "dev",
                        "apiGatewayToolConfiguration": {
                            "toolFilters": [
                                # List-all endpoints
                                {"filterPath": "/api/metrics/s3", "methods": ["GET"]},
                                {"filterPath": "/api/metrics/dynamodb", "methods": ["GET"]},
                                {"filterPath": "/api/metrics/lambda", "methods": ["GET"]},
                                # Specific resource endpoints
                                {"filterPath": "/api/metrics/s3/{bucket_name}", "methods": ["GET"]},
                                {"filterPath": "/api/metrics/dynamodb/{table_name}", "methods": ["GET"]},
                                {"filterPath": "/api/metrics/lambda/{function_name}", "methods": ["GET"]}
                            ],
                            "toolOverrides": [
                                # List-all tools
                                {
                                    "name": "Get_All_S3_Metrics",
                                    "path": "/api/metrics/s3",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for ALL S3 buckets including storage size and object count. Use this to see metrics for all buckets at once."
                                },
                                {
                                    "name": "Get_All_DynamoDB_Metrics",
                                    "path": "/api/metrics/dynamodb",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for ALL DynamoDB tables including read/write capacity and throttled requests. Use this to see metrics for all tables at once."
                                },
                                {
                                    "name": "Get_All_Lambda_Metrics",
                                    "path": "/api/metrics/lambda",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for ALL Lambda functions including invocations, duration, and errors. Use this to see metrics for all functions at once."
                                },
                                # Specific resource tools
                                {
                                    "name": "Get_S3_Bucket_Metrics",
                                    "path": "/api/metrics/s3/{bucket_name}",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for a SPECIFIC S3 bucket by name. Use this when user asks for metrics of a particular bucket like 'my-bucket-name'."
                                },
                                {
                                    "name": "Get_DynamoDB_Table_Metrics",
                                    "path": "/api/metrics/dynamodb/{table_name}",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for a SPECIFIC DynamoDB table by name. Use this when user asks for metrics of a particular table like 'UserProfiles'."
                                },
                                {
                                    "name": "Get_Lambda_Function_Metrics",
                                    "path": "/api/metrics/lambda/{function_name}",
                                    "method": "GET",
                                    "description": "Get CloudWatch metrics for a SPECIFIC Lambda function by name. Use this when user asks for metrics of a particular function like 'my-function'."
                                }
                            ]
                        }
                    }
                }
            },
            credentialProviderConfigurations=[
                {"credentialProviderType": "GATEWAY_IAM_ROLE"}
            ]
        )
        
        target_id = create_gateway_target_response['targetId']
        
        print("Gateway Target created successfully!")
        print(f"Target ID: {target_id}")
        
        print("Waiting for target to be ready...")
        status = utils.wait_for_gateway_target_ready(gateway_client, gateway_id, target_id)
        
        if status == 'READY':
            print("Target is now READY!")
        else:
            print(f"Target status: {status}")
        
        if "targets" not in config:
            config["targets"] = {}
        
        config["targets"]["iam_target"] = {
            "id": target_id,
            "name": IAM_TARGET_NAME,
            "api_id": api_id,
            "status": status
        }
        
    except gateway_client.exceptions.ConflictException:
        print(f"Target '{IAM_TARGET_NAME}' already exists.")
        
        list_response = gateway_client.list_gateway_targets(
            gatewayIdentifier=gateway_id,
            maxResults=50
        )
        for target in list_response.get('items', []):
            if target['name'] == IAM_TARGET_NAME:
                target_id = target['targetId']
                status = target['status']
                print("Found existing target!")
                print(f"Target ID: {target_id}")
                print(f"Status: {status}")
                
                if "targets" not in config:
                    config["targets"] = {}
                
                config["targets"]["iam_target"] = {
                    "id": target_id,
                    "name": IAM_TARGET_NAME,
                    "api_id": api_id,
                    "status": status
                }
                break
    
    except Exception as e:
        print(f"Error creating IAM gateway target: {e}")
        return None
    
    return config


def create_apikey_target(config, gateway_client, gateway_id, api_id):
    """Part 3: Create Gateway Target for API Key-authorized endpoints."""
    print("=" * 70)
    print("Part 3: Create Gateway Target - API Key-Authorized Endpoints")
    print("=" * 70)
    print(f"Target Name: {APIKEY_TARGET_NAME}")
    print(f"Endpoints: /api/metrics/report")
    
    credential_provider_arn = config["credential_provider"]["arn"]
    print(f"Using Credential Provider ARN: {credential_provider_arn}")
    
    print("Creating Gateway Target for API Key-authorized endpoints...")
    
    try:
        create_gateway_target_response = gateway_client.create_gateway_target(
            name=APIKEY_TARGET_NAME,
            gatewayIdentifier=gateway_id,
            targetConfiguration={
                "mcp": {
                    "apiGateway": {
                        "restApiId": api_id,
                        "stage": "dev",
                        "apiGatewayToolConfiguration": {
                            "toolFilters": [
                                {"filterPath": "/api/metrics/report", "methods": ["GET"]}
                            ],
                            "toolOverrides": [
                                {
                                    "name": "Get_Metrics_Report",
                                    "path": "/api/metrics/report",
                                    "method": "GET",
                                    "description": "Get a consolidated metrics report for all AWS resources including S3, DynamoDB, and Lambda"
                                }
                            ]
                        }
                    }
                }
            },
            credentialProviderConfigurations=[
                {
                    "credentialProviderType": "API_KEY",
                    "credentialProvider": {
                        "apiKeyCredentialProvider": {
                            "providerArn": credential_provider_arn,
                            "credentialParameterName": "x-api-key",
                            "credentialLocation": "HEADER"
                        }
                    }
                }
            ]
        )
        
        target_id = create_gateway_target_response['targetId']
        
        print("Gateway Target created successfully!")
        print(f"Target ID: {target_id}")
        
        print("Waiting for target to be ready...")
        status = utils.wait_for_gateway_target_ready(gateway_client, gateway_id, target_id)
        
        if status == 'READY':
            print("Target is now READY!")
        else:
            print(f"Target status: {status}")
        
        if "targets" not in config:
            config["targets"] = {}
        
        config["targets"]["apikey_target"] = {
            "id": target_id,
            "name": APIKEY_TARGET_NAME,
            "api_id": api_id,
            "status": status
        }
        
    except gateway_client.exceptions.ConflictException:
        print(f"Target '{APIKEY_TARGET_NAME}' already exists.")
        
        list_response = gateway_client.list_gateway_targets(
            gatewayIdentifier=gateway_id,
            maxResults=50
        )
        for target in list_response.get('items', []):
            if target['name'] == APIKEY_TARGET_NAME:
                target_id = target['targetId']
                status = target['status']
                print("Found existing target!")
                print(f"Target ID: {target_id}")
                print(f"Status: {status}")
                
                if "targets" not in config:
                    config["targets"] = {}
                
                config["targets"]["apikey_target"] = {
                    "id": target_id,
                    "name": APIKEY_TARGET_NAME,
                    "api_id": api_id,
                    "status": status
                }
                break
    
    except Exception as e:
        print(f"Error creating API Key gateway target: {e}")
        return None
    
    return config


def main():
    print("=" * 70)
    print("AgentCore Gateway Setup - Step 2")
    print("Credential Provider + Gateway Targets Creation")
    print("=" * 70)
    print(f"Region: {REGION}")
    
    # Load existing configuration
    config = utils.load_config()
    if not config:
        print("Error: Configuration not found. Please run 01_setup_gateway.py first.")
        return None
    
    if "gateway" not in config:
        print("Error: Gateway configuration not found. Please run 01_setup_gateway.py first.")
        return None
    
    gateway_id = config["gateway"]["id"]
    print(f"Gateway ID: {gateway_id}")
    
    # Get API Gateway ID from .env
    if not API_ID:
        print("Error: Could not find API Gateway ID.")
        print("Please set RESOURCE_METRICS_API_ID in .env file.")
        return None
    
    print(f"API Gateway ID: {API_ID}")
    
    # Create Gateway client
    gateway_client = boto3.client('bedrock-agentcore-control', region_name=REGION)
    
    # Part 1: Create Credential Provider
    config = create_credential_provider(config)
    if not config:
        return None
    
    # Part 2: Create IAM Target
    config = create_iam_target(config, gateway_client, gateway_id, API_ID)
    if not config:
        return None
    
    # Part 3: Create API Key Target
    config = create_apikey_target(config, gateway_client, gateway_id, API_ID)
    if not config:
        return None
    
    # Save API Gateway info
    config["api_gateway"] = {
        "id": API_ID,
        "stage": "dev"
    }
    
    # Save configuration
    utils.save_config(config)
    
    print("=" * 70)
    print("Step 2 Complete - All Targets Created!")
    print("=" * 70)
    print(f"Credential Provider ARN: {config['credential_provider']['arn']}")
    print(f"IAM Target ID: {config['targets']['iam_target']['id']}")
    print(f"IAM Target Status: {config['targets']['iam_target']['status']}")
    print(f"API Key Target ID: {config['targets']['apikey_target']['id']}")
    print(f"API Key Target Status: {config['targets']['apikey_target']['status']}")
    print("Next step: Run 03_verify_gateway_targets.py to verify all targets are ready")
    
    return config


if __name__ == "__main__":
    main()
