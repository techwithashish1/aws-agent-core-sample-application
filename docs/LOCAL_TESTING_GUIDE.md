# Local Testing Guide

This guide shows how to test the AWS Agent Core Sample Application locally before deploying to AWS.

## Prerequisites

1. **Python Environment**: Python 3.11 or higher
2. **AWS Credentials**: Configured via AWS CLI or environment variables
3. **AWS Bedrock Access**: Access to Claude 3 Sonnet model in your AWS account
4. **Dependencies Installed**: All packages from `requirements.txt`

## Setup Steps

### 1. Install Dependencies

From the project root directory:

```powershell
pip install -r requirements.txt
```

### 2. Configure AWS Credentials

Ensure your AWS credentials are configured:

```powershell
# Option 1: AWS CLI
aws configure

# Option 2: Environment Variables
$env:AWS_ACCESS_KEY_ID="YOUR_ACCESS_KEY_HERE"
$env:AWS_SECRET_ACCESS_KEY="YOUR_SECRET_ACCESS_KEY_HERE"
$env:AWS_DEFAULT_REGION="us-east-1"
```

### 3. Verify Bedrock Access

Check that you have access to Claude 3 Sonnet:

```powershell
aws bedrock list-foundation-models --region us-east-1
```

Look for `anthropic.claude-3-sonnet-20240229-v1:0` in the output.

## Running the Application Locally

### Interactive CLI Mode

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
- `List all EC2 instances in us-east-1`

**Exit:** Type `exit` or `quit` to stop the agent.

### Programmatic Usage

Use the example scripts:

```powershell
cd src
python examples/usage_examples.py
```

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

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'src'`

**Solution:** Make sure you're running commands from the `src/` directory, not the project root.

```powershell
# WRONG (from project root)
python src/main.py

# CORRECT (from src directory)
cd src
python main.py
```

### AWS Credential Errors

**Problem:** `Unable to locate credentials`

**Solution:** Configure AWS credentials using one of these methods:
1. Run `aws configure`
2. Set environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
3. Use AWS IAM role (if running on EC2)

### Bedrock Access Errors

**Problem:** `AccessDeniedException` or model not found

**Solution:** 
1. Ensure Bedrock is available in your region (`us-east-1` recommended)
2. Request access to Claude 3 Sonnet in Bedrock console
3. Wait for access approval (may take a few minutes)
4. Verify with: `aws bedrock list-foundation-models --region us-east-1`

### Package Installation Issues

**Problem:** Cannot install `langchain-aws` or other packages

**Solution:** 
1. Update pip: `pip install --upgrade pip`
2. Try with specific index: `pip install langchain-aws --index-url https://pypi.org/simple`
3. Check network/proxy settings

## Local vs AWS Deployment

### What Works Locally

✅ **Full Agent Functionality**
- All 18 MCP tools (S3, Lambda, DynamoDB, EC2, etc.)
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
├── mcp_tools/                 # All 18 MCP tools
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

## Next Steps

1. ✅ Test locally using this guide
2. ✅ Verify all tools work with your AWS account
3. ✅ Run the test suite
4. ✅ Review [README.md](README.md) for architecture details
5. ✅ See [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) for implementation details
6. 🚀 Deploy to AWS using deployment scripts (see deployment/ directory)

## Support

For issues or questions:
1. Check [README.md](README.md) for architecture overview
2. Review [CODE_DOCUMENTATION.md](CODE_DOCUMENTATION.md) for detailed implementation
3. Check CloudWatch logs for AWS deployment issues
4. Verify AWS service quotas and permissions
