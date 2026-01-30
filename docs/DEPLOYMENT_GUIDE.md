# Deployment Guide

This guide covers deploying the AWS Resource Manager agent to AWS Bedrock AgentCore.

**🚀 Deploy in 5 Minutes** - Follow the quick start steps below!

> **Note**: The code for the External APIs (Resource Utilization Reporting) used by Gateway Tools is available at: [https://github.com/techwithashish1/resource-utlization-reporting-app](https://github.com/techwithashish1/resource-utlization-reporting-app)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Detailed Deployment Steps](#detailed-deployment-steps)
4. [AgentCore Gateway Setup](#agentcore-gateway-setup)
5. [AgentCore Identity](#agentcore-identity)
6. [Common Commands](#common-commands)
7. [Configuration](#configuration)
8. [Monitoring & Operations](#monitoring--operations)
9. [Security](#security)

---

## Prerequisites

- **Python 3.11+** installed
- **AWS Account** with appropriate permissions
- **AWS CLI** configured (`aws configure`)
- **AWS Bedrock Access** enabled
- **Model Access** - Claude 3 Sonnet approved
- **IAM Permissions** for Cognito, IAM, and Bedrock AgentCore

---

## Quick Start

### Step 1: Install Dependencies

```bash
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit

# Setup virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r src/requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your AWS credentials
```

### Step 2: Setup AgentCore Gateway

```bash
cd src/agentcore_gateway

# Create IAM Role, Cognito User Pool, and Gateway
python 01_setup_gateway.py
```

This creates:
- **IAM Role**: For AgentCore Gateway permissions
- **Cognito User Pool**: For JWT-based authentication
- **Resource Server & Client**: For OAuth2 client credentials flow
- **AgentCore Gateway**: With MCP protocol support

### Step 3: Create Gateway Targets

```bash
# Set environment variables for API Gateway
export RESOURCE_METRICS_API_KEY=your-api-key
export RESOURCE_METRICS_API_ID=your-api-id

# Create credential providers and targets
python 02_create_targets.py
```

This creates:
- **API Key Credential Provider**: For API key-authorized endpoints
- **IAM Target**: For AWS service endpoints (S3, DynamoDB, Lambda)
- **API Key Target**: For custom API endpoints

### Step 4: Deploy Agent

```bash
cd ../  # Back to src directory
agentcore configure -e agentcore_entrypoint.py
agentcore deploy
```

### Step 5: Test

```bash
agentcore invoke '{"prompt":"List all S3 buckets"}'

# Or test locally with gateway tools
python test_agent_local.py
```

---

## Detailed Deployment Steps

### Step 1: Enable Bedrock Model Access

Verify Bedrock access using AWS CLI. If model list is empty, enable in AWS Console:
1. Go to AWS Bedrock console
2. Click "Model access" in left menu
3. Click "Manage model access"
4. Enable "Anthropic Claude 3 Sonnet"
5. Click "Save changes"

### Step 2: Install Dependencies

Install AgentCore CLI and Python dependencies:
1. Install `bedrock-agentcore` and `bedrock-agentcore-starter-toolkit`
2. Install requirements from `src/requirements.txt`
3. Copy `.env.example` to `.env` and edit with your AWS credentials

### Step 3: Setup AgentCore Gateway

Run the gateway setup scripts from `src/agentcore_gateway`:
1. Run `01_setup_gateway.py` - Creates IAM Role, Cognito User Pool, and Gateway
2. Run `02_create_targets.py` - Creates credential providers and targets

See [AgentCore Gateway Setup](#agentcore-gateway-setup) for details.

### Step 4: Configure Agent

Navigate to `src/` directory and run `agentcore configure -e agentcore_entrypoint.py`.

**Interactive prompts**:
- Agent Name: `aws-resource-manager`
- AWS Region: `us-east-1` (or your region)
- Memory (MB): `2048`
- Timeout (seconds): `300`

### Step 5: Deploy to AWS

Run `agentcore deploy` to deploy your agent.

**What happens**:
1. ✅ Validates Python code
2. ✅ Packages application (src/ + requirements.txt)
3. ✅ Uploads to S3 (managed by AWS)
4. ✅ Creates IAM role with permissions
5. ✅ Deploys AgentCore Runtime
6. ✅ Configures CloudWatch logging
7. ✅ Returns Agent ID

### Step 6: Test Agent

Use `agentcore invoke` to test your agent with various prompts:
- List S3 buckets
- Create S3 bucket with versioning
- List Lambda functions
- Get metrics for resources

---

## AgentCore Gateway Setup

AgentCore Gateway enables agents to access **existing APIs** as MCP tools with secure authentication.

### Why Use AgentCore Gateway?

| Challenge | Gateway Solution |
|-----------|------------------|
| **Credential Management** | Centralized credential storage with automatic rotation |
| **Authentication Complexity** | Built-in support for IAM, API Keys, and OAuth2 |
| **Security Boundaries** | Network isolation between agents and backend services |
| **Protocol Translation** | Unified MCP interface regardless of backend protocol |
| **Audit & Compliance** | Comprehensive logging of all tool invocations |

### Gateway Architecture

**Components:**
- **Agent Request** → Cognito JWT Auth → AgentCore Gateway
- **Targets:**
  - IAM Target → AWS Services (S3, DynamoDB, Lambda)
  - API Key Target → Custom APIs (API Gateway endpoints)
  - OAuth Target → Third-Party (GitHub, Slack, Google APIs)

### Gateway Components

| Component | Description | Purpose |
|-----------|-------------|---------|
| **Gateway** | Central routing hub | Routes authenticated requests to appropriate targets |
| **IAM Role** | Service-linked role | Grants gateway permissions to assume target roles |
| **Cognito User Pool** | Identity provider | Issues JWT tokens for gateway authentication |
| **Resource Server** | OAuth2 configuration | Defines scopes for access control |
| **Credential Provider** | Secret storage | Securely stores API keys and secrets |
| **Targets** | Backend endpoints | Define how to reach AWS services or external APIs |

### Target Types

#### 1. IAM Target (AWS Services)
Uses AWS IAM for authentication. Ideal for accessing AWS services like S3, Lambda, DynamoDB, and CloudWatch metrics.

#### 2. API Key Target (Custom APIs)
Uses API keys stored in Secrets Manager. Ideal for custom API Gateway endpoints.

#### 3. OAuth Target (Third-Party Services)
Uses OAuth2 token exchange. Ideal for third-party integrations like GitHub, Slack.

### Setup Steps

#### Step 1: Setup Gateway Infrastructure

Run `01_setup_gateway.py` from the `src/agentcore_gateway` directory.

**Creates:**
- IAM Role with trust policy for AgentCore
- Cognito User Pool with domain
- Resource Server with `invoke` scope
- App Client with client credentials flow
- AgentCore Gateway with MCP protocol
- `gateway_config.json` with all configuration

#### Step 2: Create Gateway Targets

Set environment variables for API Gateway (if using external endpoints), then run `02_create_targets.py`.

**Creates:**
- API Key Credential Provider (stored in Secrets Manager)
- IAM Target for AWS service metrics
- API Key Target for custom API endpoints

### Gateway Configuration

After setup, a `gateway_config.json` file is generated containing:
- Region and gateway name
- Gateway ARN
- IAM role ARN and name
- Cognito user pool ID, client ID, client secret, and token endpoint
- Target ARNs (IAM target, API key target)

### Using Gateway Tools

Initialize the `AWSResourceAgent` with `include_gateway_tools=True` to enable gateway-exposed MCP tools.

---

## Common Commands

### Agent Operations
```bash
# Invoke agent
agentcore invoke '{"prompt":"YOUR_COMMAND_HERE"}'

# View logs
agentcore logs --follow

# Check status
agentcore status

# Update code
agentcore update

# Delete agent
agentcore destroy
```

### Example Commands

#### S3 Operations
```bash
agentcore invoke '{"prompt":"Create S3 bucket named my-app-data with versioning enabled"}'
agentcore invoke '{"prompt":"List all S3 buckets"}'
agentcore invoke '{"prompt":"Show details for bucket my-app-data"}'
```

#### Lambda Operations
```bash
agentcore invoke '{"prompt":"Create Lambda function named data-processor with Python 3.11 runtime"}'
agentcore invoke '{"prompt":"List all Lambda functions"}'
agentcore invoke '{"prompt":"Update Lambda function data-processor to use 512MB memory"}'
```

#### DynamoDB Operations
```bash
agentcore invoke '{"prompt":"Create DynamoDB table named Users with partition key userId (string)"}'
agentcore invoke '{"prompt":"List all DynamoDB tables"}'
agentcore invoke '{"prompt":"Show details for DynamoDB table Users"}'
```

#### Metrics Operations
```bash
agentcore invoke '{"prompt":"Show metrics for S3 bucket my-app-data"}'
agentcore invoke '{"prompt":"Show metrics for Lambda function data-processor"}'
agentcore invoke '{"prompt":"Show metrics for DynamoDB table Users"}'
```

---

## Configuration

### Environment Variables (.env)
```env
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=123456789012
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
BEDROCK_REGION=us-east-1
MAX_TOKENS=4096
TEMPERATURE=0.7
```

### AgentCore Config (src/.agentcoreconfig)
```yaml
agent_name: aws-resource-manager
entrypoint: agentcore_entrypoint.py
python_version: "3.11"
memory_size: 2048
timeout: 300
```

---

## AgentCore Identity

AgentCore Identity provides workload identity management for AI agents. It enables secure authentication when agents access **Gateway Tools**.

### What is AgentCore Identity?

When the agent uses Gateway Tools to access existing APIs, AgentCore Identity answers "who is calling?" by providing:

- **Workload Identity**: Unique identity for each agent workload
- **Token Exchange**: Convert agent tokens to service-specific credentials
- **Identity Federation**: Integrate with external identity providers
- **Audit Trail**: Track which agent performed which action

### Why Use AgentCore Identity?

| Traditional Approach | AgentCore Identity Approach |
|---------------------|----------------------------|
| Hardcoded credentials in code | Dynamic, short-lived tokens |
| Shared service accounts | Unique identity per agent instance |
| Manual credential rotation | Automatic token refresh |
| Limited audit capability | Full identity chain tracing |
| Complex OAuth flows | Simplified token exchange |

### Identity Components

| Component | Description | Purpose |
|-----------|-------------|---------|
| **Workload Token** | Agent's base identity token | Proves agent identity within AgentCore |
| **Token Exchange Service** | Converts between token types | Exchanges workload token for target credentials |
| **Identity Provider** | External IdP integration | Federate with Cognito, Okta, Azure AD, etc. |
| **Service Token** | Target-specific credential | JWT or OAuth token for accessing services |

### Token Exchange Flow

1. Agent receives Workload Token from AgentCore Runtime
2. Agent requests Token Exchange with target scope
3. AgentCore Identity validates Workload Token
4. Identity Service checks authorization policies
5. Token Exchange Service generates Service Token
6. Agent uses Service Token to call Target Service

### Integration with Gateway

AgentCore Identity works seamlessly with AgentCore Gateway:

1. Get workload identity from environment using `AgentIdentity.from_environment()`
2. Exchange workload token for gateway access token with appropriate scopes
3. Use the token with the GatewayClient to make authenticated requests

### Identity Provider Federation

#### Cognito Integration (Default)
Automatic when using AgentCore Gateway. Configure with provider type "COGNITO", user pool ID, and client ID.

#### Custom OAuth2 Provider
For enterprise IdP integration, configure with provider type "OAUTH2" and provide issuer, authorization endpoint, token endpoint, and JWKS URI.

### Use Cases

1. **User Context Propagation**: Pass user identity through the agent to backend services
2. **Service-to-Service Authentication**: Agent authenticates to external services via token exchange
3. **Cross-Account Access**: Access resources in different AWS accounts using `assume_role`

### Security Considerations

| Aspect | Implementation |
|--------|----------------|
| **Token Lifetime** | Short-lived (1 hour default), auto-refresh |
| **Scope Limitation** | Tokens limited to requested scopes only |
| **Audience Restriction** | Tokens valid only for specified target |
| **Revocation** | Immediate revocation capability via Identity API |
| **Audit Logging** | All token exchanges logged to CloudTrail |

---

## Monitoring & Operations

### View Logs

Use `agentcore logs` command with options:
- `--follow`: Stream real-time logs
- `--tail <n>`: Get last n lines
- `--level <level>`: Filter by level (ERROR, INFO)
- `--filter <string>`: Search logs

### Check Agent Status

Use `agentcore status` for agent information and `agentcore healthcheck` for health check.

### Update Agent

After making code changes, run `agentcore update` to redeploy.

### Metrics & Performance

CloudWatch metrics available:
- Invocation count
- Success/failure rate
- Execution time (avg/max/min)
- LLM token usage
- Tool execution count

### Cleanup

Run `agentcore destroy` to delete agent and all resources.

---

## Security

### IAM Permissions

#### Agent Runtime Permissions
The agent needs `bedrock:InvokeModel` and `bedrock:InvokeModelWithResponseStream` permissions for Claude 3 Sonnet foundation model.

#### Gateway Setup Permissions (for running setup scripts)
Requires permissions for:
- IAM role management (CreateRole, GetRole, AttachRolePolicy, PutRolePolicy)
- Cognito management (CreateUserPool, CreateUserPoolClient, CreateUserPoolDomain, CreateResourceServer, etc.)
- AgentCore Gateway (CreateGateway, CreateGatewayTarget, CreateApiKeyCredentialProvider, etc.)
- Secrets Manager (CreateSecret, GetSecretValue)

#### Gateway Target Permissions (for AWS service access)
The gateway role needs read permissions for:
- S3: ListAllMyBuckets, GetBucketLocation, GetBucketVersioning, etc.
- Lambda: ListFunctions, GetFunction, GetFunctionConfiguration
- DynamoDB: ListTables, DescribeTable
- CloudWatch: GetMetricStatistics, ListMetrics

See [agent-permissions-policy.json](../agent-permissions-policy.json) for complete IAM policy.

### Gateway Authentication Security

- **JWT-based Authentication**: All gateway requests authenticated via Cognito
- **Client Credentials Flow**: OAuth2 client credentials for machine-to-machine auth
- **Token Expiration**: Access tokens expire after 1 hour
- **Secure Secret Storage**: Client secrets stored in Secrets Manager

### Identity Security

- **Workload Identity Isolation**: Each agent instance has unique identity
- **Token Binding**: Tokens bound to specific workload context
- **Scope Enforcement**: Minimal scopes granted per operation
- **Audit Trail**: Complete identity chain logged for compliance

### Data Protection

- ✅ **No Data Access**: System cannot access S3 objects or DynamoDB items
- ✅ **Infrastructure Only**: Limited to bucket/table/function management
- ✅ **Gateway Authentication**: All tool calls go through authenticated gateway
- ✅ **Identity Verification**: Every request tied to verified identity
- ✅ **Encryption**: Enables encryption by default for S3 buckets
- ✅ **Public Access Blocking**: Automatically blocks public S3 access
- ✅ **Audit Logging**: All operations logged to CloudWatch

### Best Practices

1. **Enable MFA** for AWS account
2. **Use least-privilege IAM** roles
3. **Enable CloudTrail** for audit logs
4. **Review logs regularly** for suspicious activity
5. **Rotate Cognito client secrets** periodically
6. **Monitor gateway access** via CloudWatch
7. **Implement token refresh** before expiration
8. **Use short-lived tokens** for all operations
9. **Validate identity claims** in backend services
10. **Use tags** for resource organization and cost tracking

---

## Related Documentation

- [README.md](../README.md) - Project overview and architecture
- [TESTING_GUIDE.md](TESTING_GUIDE.md) - Usage examples, local testing, and troubleshooting
