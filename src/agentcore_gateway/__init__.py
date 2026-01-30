"""
AgentCore Gateway Setup Package

This package contains scripts to set up AgentCore Gateway for the Resource Metrics API.
Based on AWS AgentCore samples: https://github.com/awslabs/amazon-bedrock-agentcore-samples

Scripts should be executed in order:
    1. 01_create_iam_role.py      - Create IAM Role for Gateway
    2. 02_setup_cognito.py        - Configure Cognito for authentication
    3. 03_create_gateway.py       - Create the AgentCore Gateway
    4. 04_create_credential_provider.py - Create API Key credential provider
    5. 05_create_gateway_target_iam.py  - Create IAM-authorized target
    6. 06_create_gateway_target_apikey.py - Create API Key-authorized target
    7. 07_verify_gateway_targets.py     - Verify all targets are ready
"""

__version__ = "1.0.0"
