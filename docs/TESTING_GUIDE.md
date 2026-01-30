# Testing Guide

This guide covers usage examples, local testing setup, testing procedures, and troubleshooting for the AWS Resource Manager agent.

> **Note**: The code for the External APIs (Resource Utilization Reporting) used by Gateway Tools is available at: [https://github.com/techwithashish1/resource-utlization-reporting-app](https://github.com/techwithashish1/resource-utlization-reporting-app)

---

## Table of Contents

1. [Usage Examples](#usage-examples)
2. [Local Testing Setup](#local-testing-setup)
3. [Testing Gateway Integration](#testing-gateway-integration)
4. [Running Tests](#running-tests)
5. [Local vs AWS Deployment](#local-vs-aws-deployment)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

---

## Usage Examples

### Example 1: Create S3 Bucket

Send a prompt like: "Create an S3 bucket named my-app-data-2026 with versioning and encryption enabled"

**Agent Flow**:
1. User input received
2. LLM analyzes: "Need to create S3 bucket" ⚡
3. LLM selects: CreateS3BucketTool ⚡
4. Tool executes: boto3.create_bucket()
5. LLM generates response: "Successfully created..." ⚡

### Example 2: List Lambda Functions

Send a prompt like: "List all Lambda functions in my account"

The agent returns a formatted list with runtime, memory, timeout, and last modified date for each function.

### Example 3: Create DynamoDB Table

Send a prompt like: "Create a DynamoDB table named Users with partition key userId (string) and sort key timestamp (number)"

The agent creates the table and returns confirmation with table ARN and status.

### Example 4: Get Metrics (Gateway Tool)

Send a prompt like: "Show me metrics for Lambda function data-processor-function for the last 7 days"

The agent uses Gateway Tools to fetch metrics:
1. AgentCore Identity provides workload token
2. Token exchanged for Cognito JWT
3. Gateway authenticates and routes to IAM Target
4. CloudWatch API returns metrics
5. Agent formats and returns invocation counts, error rates, and performance statistics

### Example 5: Complex Multi-Step Command

Send a prompt like: "Create an S3 bucket for analytics, then create a Lambda function to process the data, and show me the current metrics"

**Agent Flow**:
1. LLM breaks down into 3 steps ⚡
2. Step 1: Create S3 bucket (CreateS3BucketTool - Local)
3. Step 2: Create Lambda function (CreateLambdaFunctionTool - Local)
4. Step 3: Get metrics (Gateway Tool via AgentCore Gateway)
5. LLM generates summary ⚡

---

## Local Testing Setup

### Prerequisites

1. **Python Environment**: Python 3.11 or higher
2. **AWS Credentials**: Configured via AWS CLI or environment variables
3. **AWS Bedrock Access**: Access to Claude 3 Sonnet model in your AWS account
4. **Dependencies Installed**: All packages from `requirements.txt`

### Setup Steps

#### 1. Install Dependencies

From the project root directory:

```powershell
pip install -r requirements.txt
```

#### 2. Configure AWS Credentials

Ensure your AWS credentials are configured:

```powershell
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_HERE"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY_HERE"
$env:AWS_DEFAULT_REGION="us-east-1"
```

#### 3. Verify Bedrock Access

Check that you have access to Claude 3 Sonnet:

```powershell
aws bedrock list-foundation-models --region us-east-1
```

Look for `anthropic.claude-3-sonnet-20240229-v1:0` in the output.

### Running the Application Locally

#### Interactive CLI Mode

Run the agent from the `src/` directory:

```powershell
cd src
python main.py
```

**Example Commands to Try:**
- `List all S3 buckets`
- `Create an S3 bucket named test-bucket-12345 in us-east-1`
- `List all Lambda functions`
- `Get information about DynamoDB table MyTable`

**Exit:** Type `exit` or `quit` to stop the agent.

#### Programmatic Usage

Use the example scripts:

```powershell
cd src
python examples/usage_examples.py
```

---

## Testing Gateway Integration

### Test Gateway Connection

Test gateway connection and tools using `test_integration.py`:

```powershell
cd src/gateway_integration
python test_integration.py
```

### Test with Local Agent

Use the local test script:

```powershell
python src/test_agent_local.py
```

### Verify Gateway Configuration

Check that `gateway_config.json` exists in `src/agentcore_gateway` with:
- Gateway ARN
- Cognito credentials
- Target ARNs

---

## Running Tests

### Prerequisites for Tests

Tests use `moto` for mocking AWS services. Ensure it's installed:

```powershell
pip install pytest pytest-asyncio moto
```

### Run All Tests

From the `src/` directory:

```powershell
cd src
pytest tests/ -v
```

### Run Specific Test Files

```powershell
# S3 tools tests
pytest tests/test_s3_tools.py -v

# Lambda tools tests
pytest tests/test_lambda_tools.py -v

# DynamoDB tools tests
pytest tests/test_dynamodb_tools.py -v
```

### Run with Coverage

```powershell
pytest tests/ --cov=. --cov-report=html
```

---

## Local vs AWS Deployment

### What Works Locally

✅ **Full Agent Functionality**
- All MCP tools (S3, Lambda, DynamoDB)
- Langgraph StateGraph orchestration
- ChatBedrock LLM integration
- Tool calling and execution
- Interactive CLI testing

✅ **Unit Tests**
- Mocked AWS services (via `moto`)
- Tool execution tests
- Input validation tests

### Differences from AWS Deployment

| Feature | Local | AWS Bedrock Agent Core |
|---------|-------|------------------------|
| Entry Point | `main.py` | `agentcore_entrypoint.py` |
| AWS Credentials | Local config | IAM role |
| Logging | Console output | CloudWatch Logs |
| Scaling | Single instance | Auto-scaling |
| Cost | Pay for API calls | Pay for invocations + API calls |
| Deployment | N/A | Infrastructure as Code |

### When to Deploy to AWS

Deploy to AWS Bedrock Agent Core when you need:
- **Production-grade hosting**: Auto-scaling, monitoring, logging
- **Integration**: Connect with other AWS services via API Gateway
- **Cost optimization**: Pay only for actual invocations
- **Enterprise features**: VPC deployment, IAM integration, compliance

---

## Troubleshooting

### Issue: Agent not responding

**Symptoms**: No response or timeout when invoking agent

**Solutions**:
1. Check agent status: `agentcore status`
2. View recent logs: `agentcore logs --tail 50`
3. Run health check: `agentcore healthcheck`
4. Verify agent is deployed: `agentcore list`

### Issue: Import Errors

**Symptoms**: `ModuleNotFoundError: No module named 'src'`

**Solutions**: Make sure you're running commands from the `src/` directory, not the project root.

```powershell
# WRONG (from project root)
python src/main.py

# CORRECT (from src directory)
cd src
python main.py
```

### Issue: AWS Credential Errors

**Symptoms**: `Unable to locate credentials`

**Solutions**: Configure AWS credentials using one of these methods:
1. Run `aws configure`
2. Set environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
3. Use AWS IAM role (if running on EC2)

### Issue: Bedrock Access Denied

**Symptoms**: Error mentioning Bedrock access or model not available

**Solutions**:
1. Verify model access in AWS Console:
   - Go to Bedrock → Model access → Manage
   - Enable Claude 3 Sonnet
2. Check IAM permissions include `bedrock:InvokeModel`
3. Verify region matches your deployment
4. Wait for access approval (may take a few minutes)

### Issue: Tool execution failed

**Symptoms**: Agent responds but tool operations fail

**Solutions**:
1. View error logs: `agentcore logs --level ERROR`
2. Common causes:
   - IAM permissions missing for the target service
   - Resource doesn't exist
   - Invalid parameters in request
   - Gateway authentication failed
   - Cognito token expired

### Issue: Gateway Authentication Failed

**Symptoms**: Error related to JWT, Cognito, or gateway authentication

**Solutions**:
1. Verify `gateway_config.json` exists:
   ```powershell
   cat src/agentcore_gateway/gateway_config.json
   ```
2. Test Cognito token generation manually
3. Re-run gateway setup if needed:
   ```powershell
   cd src/agentcore_gateway
   python 01_setup_gateway.py
   python 02_create_targets.py
   ```
4. Check Cognito User Pool is active in AWS Console

### Issue: Identity Token Exchange Failed

**Symptoms**: Error related to workload token or token exchange

**Solutions**:
1. Check identity configuration: `agentcore identity status`
2. Review token exchange logs: `agentcore logs --filter "token_exchange"`
3. Common causes:
   - Invalid workload token (agent not running in AgentCore)
   - Scope not authorized in Cognito Resource Server
   - Target audience mismatch between request and configuration

### Issue: Local Tools Work, Gateway Tools Fail

**Symptoms**: Operations like CreateS3Bucket work, but metrics endpoints fail

**Solutions**:
1. This indicates gateway setup issue, not agent issue
2. Verify gateway targets exist: Check `gateway_config.json` for target ARNs
3. Test gateway directly:
   ```powershell
   python src/gateway_integration/test_integration.py
   ```
4. Check IAM Target permissions allow CloudWatch access

### Issue: Metrics Report Not Available

**Symptoms**: `/api/metrics/report` endpoint fails with API Key error

**Solutions**:
1. Verify API Key Credential Provider was created
2. Check Secrets Manager for the stored API key
3. Ensure `RESOURCE_METRICS_API_KEY` environment variable was set during setup
4. Re-run `02_create_targets.py` with correct environment variables

### Issue: Slow Response Times

**Symptoms**: Agent responds but takes too long

**Solutions**:
1. Check LLM token usage in CloudWatch metrics
2. Simplify prompts to reduce reasoning steps
3. Consider using more specific tool names in prompts
4. Review agent memory allocation (increase if needed)

### Issue: Package Installation Issues

**Symptoms**: Cannot install `langchain-aws` or other packages

**Solutions**: 
1. Update pip: `pip install --upgrade pip`
2. Try with specific index: `pip install langchain-aws --index-url https://pypi.org/simple`
3. Check network/proxy settings

### Debugging Tips

1. **Enable verbose logging**: Set `LOG_LEVEL=DEBUG` in `.env`
2. **Check CloudWatch Logs**: View full execution traces
3. **Test components individually**:
   - Test Bedrock: `aws bedrock-runtime invoke-model ...`
   - Test Gateway: Run `test_integration.py`
   - Test Local Tools: Use `main.py` interactively
4. **Review IAM policies**: Ensure all required permissions are granted

---

## Best Practices

### Before Deploying to AWS

1. ✅ Test all commands locally
2. ✅ Run full test suite: `pytest tests/ -v`
3. ✅ Verify AWS resource access (S3, Lambda, DynamoDB, etc.)
4. ✅ Check CloudWatch logs configuration
5. ✅ Review IAM permissions in deployment scripts

### Development Workflow

1. **Develop**: Write code and test locally with `python main.py`
2. **Test**: Run unit tests with `pytest tests/ -v`
3. **Verify**: Test with real AWS resources
4. **Document**: Update documentation for any changes
5. **Deploy**: Use deployment scripts to push to AWS

### Cost Management

**Local Testing:**
- Only pay for AWS API calls (S3, Lambda, Bedrock, etc.)
- Bedrock Claude 3 Sonnet costs: ~$0.003 per 1K input tokens

**Recommendation:** Test with small operations first to avoid unexpected costs.

---

## Quick Reference

### Directory Structure for Testing

```
src/
├── main.py                    # Local CLI entry point
├── agentcore_entrypoint.py    # AWS deployment entry point
├── agent/
│   └── aws_agent.py           # Langgraph StateGraph agent
├── bedrock/
│   └── langchain_integration.py # ChatBedrock LLM
├── mcp_tools/                 # MCP tools (S3, Lambda, DynamoDB)
├── tests/                     # Unit tests
└── examples/                  # Usage examples
```

### Key Commands

```powershell
# Install dependencies
pip install -r requirements.txt

# Run agent locally
cd src
python main.py

# Run tests
cd src
pytest tests/ -v

# Run examples
cd src
python examples/usage_examples.py

# Check AWS credentials
aws sts get-caller-identity

# List Bedrock models
aws bedrock list-foundation-models --region us-east-1
```

---

## Related Documentation

- [README.md](../README.md) - Project overview and architecture
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) - Deployment guide and security
