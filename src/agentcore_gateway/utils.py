"""
Utility functions for AgentCore Gateway setup.
Based on AWS AgentCore samples: https://github.com/awslabs/amazon-bedrock-agentcore-samples
"""

import boto3
import json
import time
from boto3.session import Session
from botocore.exceptions import ClientError
import requests


def get_or_create_user_pool(cognito, USER_POOL_NAME):
    """
    Get or create a Cognito User Pool.
    
    :param cognito: Cognito client
    :param USER_POOL_NAME: Name of the user pool
    :return: User Pool ID
    """
    response = cognito.list_user_pools(MaxResults=60)
    for pool in response["UserPools"]:
        if pool["Name"] == USER_POOL_NAME:
            user_pool_id = pool["Id"]
            response = cognito.describe_user_pool(UserPoolId=user_pool_id)
            user_pool = response.get('UserPool', {})
            domain = user_pool.get('Domain')
            
            if domain:
                region = user_pool_id.split('_')[0] if '_' in user_pool_id else 'us-east-1'
                domain_url = f"https://{domain}.auth.{region}.amazoncognito.com"
                print(f"Found domain for user pool {user_pool_id}: {domain} ({domain_url})")
            else:
                print(f"No domains found for user pool {user_pool_id}")
            return pool["Id"]
    
    print('Creating new user pool')
    created = cognito.create_user_pool(PoolName=USER_POOL_NAME)
    user_pool_id = created["UserPool"]["Id"]
    user_pool_id_without_underscore_lc = user_pool_id.replace("_", "").lower()
    cognito.create_user_pool_domain(
        Domain=user_pool_id_without_underscore_lc,
        UserPoolId=user_pool_id
    )
    print("Domain created as well")
    return created["UserPool"]["Id"]


def get_or_create_resource_server(cognito, user_pool_id, RESOURCE_SERVER_ID, RESOURCE_SERVER_NAME, SCOPES):
    """
    Get or create a Cognito Resource Server.
    
    :param cognito: Cognito client
    :param user_pool_id: User Pool ID
    :param RESOURCE_SERVER_ID: Resource Server identifier
    :param RESOURCE_SERVER_NAME: Resource Server name
    :param SCOPES: List of scopes
    :return: Resource Server ID
    """
    try:
        existing = cognito.describe_resource_server(
            UserPoolId=user_pool_id,
            Identifier=RESOURCE_SERVER_ID
        )
        return RESOURCE_SERVER_ID
    except cognito.exceptions.ResourceNotFoundException:
        print('Creating new resource server')
        cognito.create_resource_server(
            UserPoolId=user_pool_id,
            Identifier=RESOURCE_SERVER_ID,
            Name=RESOURCE_SERVER_NAME,
            Scopes=SCOPES
        )
        return RESOURCE_SERVER_ID


def get_or_create_m2m_client(cognito, user_pool_id, CLIENT_NAME, RESOURCE_SERVER_ID, SCOPES=None):
    """
    Get or create a Machine-to-Machine Cognito client.
    
    :param cognito: Cognito client
    :param user_pool_id: User Pool ID
    :param CLIENT_NAME: Client name
    :param RESOURCE_SERVER_ID: Resource Server ID
    :param SCOPES: List of scopes
    :return: Tuple of (client_id, client_secret)
    """
    response = cognito.list_user_pool_clients(UserPoolId=user_pool_id, MaxResults=60)
    for client in response["UserPoolClients"]:
        if client["ClientName"] == CLIENT_NAME:
            describe = cognito.describe_user_pool_client(
                UserPoolId=user_pool_id, 
                ClientId=client["ClientId"]
            )
            return client["ClientId"], describe["UserPoolClient"]["ClientSecret"]
    
    print('Creating new M2M client')
    
    # Default scopes if not provided
    if SCOPES is None:
        SCOPES = [f"{RESOURCE_SERVER_ID}/gateway:read", f"{RESOURCE_SERVER_ID}/gateway:write"]

    created = cognito.create_user_pool_client(
        UserPoolId=user_pool_id,
        ClientName=CLIENT_NAME,
        GenerateSecret=True,
        AllowedOAuthFlows=["client_credentials"],
        AllowedOAuthScopes=SCOPES,
        AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"],
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH"]
    )
    return created["UserPoolClient"]["ClientId"], created["UserPoolClient"]["ClientSecret"]


def get_token(user_pool_id: str, client_id: str, client_secret: str, scope_string: str, region: str) -> dict:
    """
    Get OAuth token from Cognito.
    
    :param user_pool_id: User Pool ID
    :param client_id: Client ID
    :param client_secret: Client Secret
    :param scope_string: Scope string
    :param region: AWS region
    :return: Token response dictionary
    """
    try:
        user_pool_id_without_underscore = user_pool_id.replace("_", "").lower()
        url = f"https://{user_pool_id_without_underscore}.auth.{region}.amazoncognito.com/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": scope_string,
        }
        print(f"Requesting token for client: {client_id}")
        print(f"Token URL: {url}")
        # Note: In corporate environments with SSL proxies, you may need to set verify=False
        # or provide a custom certificate bundle
        import os
        verify = os.environ.get('SSL_VERIFY', 'true').lower() != 'false'
        response = requests.post(url, headers=headers, data=data, verify=verify)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.RequestException as err:
        return {"error": str(err)}


def create_agentcore_gateway_role(gateway_name):
    """
    Create an IAM Role for AgentCore Gateway.
    
    :param gateway_name: Name for the gateway (used in role naming)
    :return: IAM Role details
    """
    iam_client = boto3.client('iam')
    agentcore_gateway_role_name = f'agentcore-{gateway_name}-role'
    boto_session = Session()
    region = boto_session.region_name
    account_id = boto3.client("sts").get_caller_identity()["Account"]
    
    role_policy = {
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AgentCoreGatewayPolicy",
            "Effect": "Allow",
            "Action": [
                "bedrock-agentcore:*",
                "bedrock:*",
                "agent-credential-provider:*",
                "iam:PassRole",
                "secretsmanager:GetSecretValue",
                "lambda:InvokeFunction",
                "execute-api:Invoke"
            ],
            "Resource": "*"
        }]
    }

    assume_role_policy_document = {
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
                        "aws:SourceAccount": f"{account_id}"
                    },
                    "ArnLike": {
                        "aws:SourceArn": f"arn:aws:bedrock-agentcore:{region}:{account_id}:*"
                    }
                }
            }
        ]
    }

    assume_role_policy_document_json = json.dumps(assume_role_policy_document)
    role_policy_document = json.dumps(role_policy)
    
    # Create IAM Role
    try:
        agentcore_iam_role = iam_client.create_role(
            RoleName=agentcore_gateway_role_name,
            AssumeRolePolicyDocument=assume_role_policy_document_json
        )
        # Pause to make sure role is created
        time.sleep(10)
    except iam_client.exceptions.EntityAlreadyExistsException:
        print("Role already exists -- using existing role")
        agentcore_iam_role = iam_client.get_role(RoleName=agentcore_gateway_role_name)
        return agentcore_iam_role

    # Attach the role policy
    print(f"Attaching role policy to {agentcore_gateway_role_name}")
    try:
        iam_client.put_role_policy(
            PolicyDocument=role_policy_document,
            PolicyName="AgentCorePolicy",
            RoleName=agentcore_gateway_role_name
        )
    except Exception as e:
        print(f"Error attaching policy: {e}")

    return agentcore_iam_role


def wait_for_gateway_target_ready(gateway_client, gateway_id, target_id, max_wait=120, interval=5):
    """
    Wait for a gateway target to be in READY state.
    
    :param gateway_client: Bedrock AgentCore Control client
    :param gateway_id: Gateway ID
    :param target_id: Target ID
    :param max_wait: Maximum wait time in seconds
    :param interval: Polling interval in seconds
    :return: Target status
    """
    elapsed = 0
    while elapsed < max_wait:
        try:
            response = gateway_client.get_gateway_target(
                gatewayIdentifier=gateway_id,
                targetId=target_id
            )
            status = response.get('status', 'UNKNOWN')
            print(f"  Target status: {status}")
            
            if status == 'READY':
                return status
            elif status == 'FAILED':
                print(f"  Target creation failed. Reason: {response.get('statusReason', 'Unknown')}")
                return status
            
            time.sleep(interval)
            elapsed += interval
        except ClientError as e:
            print(f"  Error checking target status: {e}")
            return 'ERROR'
    
    print(f"  Timeout waiting for target to be ready")
    return 'TIMEOUT'


def save_config(config, filename='gateway_config.json'):
    """
    Save configuration to a JSON file.
    
    :param config: Configuration dictionary
    :param filename: Output filename
    """
    with open(filename, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"Configuration saved to {filename}")


def load_config(filename='gateway_config.json'):
    """
    Load configuration from a JSON file.
    
    :param filename: Input filename
    :return: Configuration dictionary
    """
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Configuration file {filename} not found")
        return None
