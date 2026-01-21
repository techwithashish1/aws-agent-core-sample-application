# AWS Resource Manager - Quick Guide

## 🚀 Deploy in 5 Minutes

```bash
# 1. Install AgentCore CLI
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit

# 2. Navigate to src and configure
cd src
agentcore configure -e agentcore_entrypoint.py

# 3. Deploy
agentcore launch

# 4. Test
agentcore invoke '{"prompt":"List all S3 buckets"}'
```

## 📋 Common Commands

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
# Create bucket
agentcore invoke '{"prompt":"Create S3 bucket named my-app-data with versioning enabled"}'

# List buckets
agentcore invoke '{"prompt":"List all S3 buckets"}'

# Get bucket info
agentcore invoke '{"prompt":"Show details for bucket my-app-data"}'

# Delete bucket
agentcore invoke '{"prompt":"Delete S3 bucket my-app-data"}'
```

#### Lambda Operations
```bash
# Create function
agentcore invoke '{"prompt":"Create Lambda function named data-processor with Python 3.11 runtime"}'

# List functions
agentcore invoke '{"prompt":"List all Lambda functions"}'

# Update config
agentcore invoke '{"prompt":"Update Lambda function data-processor to use 512MB memory and 60 second timeout"}'

# Delete function
agentcore invoke '{"prompt":"Delete Lambda function data-processor"}'
```

#### DynamoDB Operations
```bash
# Create table
agentcore invoke '{"prompt":"Create DynamoDB table named Users with partition key userId (string)"}'

# List tables
agentcore invoke '{"prompt":"List all DynamoDB tables"}'

# Describe table
agentcore invoke '{"prompt":"Show details for DynamoDB table Users"}'

# Delete table
agentcore invoke '{"prompt":"Delete DynamoDB table Users"}'
```

#### Metrics Operations
```bash
# S3 metrics
agentcore invoke '{"prompt":"Show metrics for S3 bucket my-app-data"}'

# Lambda metrics
agentcore invoke '{"prompt":"Show metrics for Lambda function data-processor"}'

# DynamoDB metrics
agentcore invoke '{"prompt":"Show metrics for DynamoDB table Users"}'
```

## 🏃 Local Development

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r src/requirements.txt

# Configure
cp .env.example .env
# Edit .env with your AWS credentials

# Run
python src/main.py
```

## ⚙️ Configuration

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

## 📊 Monitoring

```bash
# Real-time logs
agentcore logs --follow

# Last 100 lines
agentcore logs --tail 100

# Error logs only
agentcore logs --level ERROR

# Health check
agentcore healthcheck
```

## 🔧 Troubleshooting

### Issue: Bedrock Access Denied
**Solution**: Enable Bedrock model access in AWS Console → Bedrock → Model access

### Issue: Command Not Found
**Solution**: Install AgentCore CLI
```bash
pip install bedrock-agentcore bedrock-agentcore-starter-toolkit
```

### Issue: Deployment Failed
**Solution**: Check AWS credentials
```bash
aws sts get-caller-identity
aws bedrock list-foundation-models --region us-east-1
```

## 📚 More Information

See [README.md](README.md) for complete documentation including:
- Detailed architecture
- Code explanations
- All MCP tools
- Advanced configuration
- Security guidelines
