"""
Script to invoke a deployed Bedrock AgentCore agent remotely.

Usage:
    python invoke_agent.py "List all S3 buckets in asia pacific region"
    python invoke_agent.py "Show encrypted buckets with versioning enabled"
"""

import boto3
import json
import sys
import uuid
import os

# Configuration - Update these values with your agent details or set environment variables
# Example: export AGENT_ARN="arn:aws:bedrock-agentcore:region:account:runtime/agent-id"
AGENT_ARN = os.environ.get("AGENT_ARN", "arn:aws:bedrock-agentcore:ap-south-1:YOUR_ACCOUNT_ID:runtime/YOUR_AGENT_ID")
AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")


def invoke_agent(prompt: str, agent_arn: str = AGENT_ARN, region: str = AWS_REGION):
    """
    Invoke a Bedrock AgentCore agent with the given prompt.
    
    Args:
        prompt: The user's query/prompt
        agent_arn: ARN of the deployed agent runtime
        region: AWS region where the agent is deployed
    """
    # Initialize the Bedrock AgentCore client
    agent_core_client = boto3.client('bedrock-agentcore', region_name=region)
    
    # Generate a unique session ID (must be at least 33 characters)
    session_id = f"session-{uuid.uuid4()}"
    
    print(f"Invoking agent: {agent_arn}")
    print(f"Prompt: {prompt}")
    print(f"Session ID: {session_id}")
    
    # Prepare the payload
    payload = json.dumps({"prompt": prompt}).encode()
    
    try:
        # Invoke the agent
        response = agent_core_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id,
            payload=payload
        )
        
        # Process and print the response
        if "text/event-stream" in response.get("contentType", ""):
            # Handle streaming response
            print("Streaming response:")
            content = []
            for line in response["response"].iter_lines(chunk_size=10):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        line = line[6:]
                        print(line)
                        content.append(line)
            
            print("Complete response:")
            print("\n".join(content))
        
        elif response.get("contentType") == "application/json":
            # Handle standard JSON response
            content = []
            for chunk in response.get("response", []):
                content.append(chunk.decode('utf-8'))
            
            response_data = json.loads(''.join(content))
            print("JSON response:")
            print(json.dumps(response_data, indent=2))
        
        else:
            # Print raw response for other content types
            print("Unexpected content type. Raw response:")
            print(response)
    
    except Exception as e:
        print(f"Error invoking agent: {str(e)}")
        raise


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python invoke_agent.py <your prompt here>")
        print("Examples:")
        print('  python invoke_agent.py List all S3 buckets in asia pacific region')
        print('  python invoke_agent.py Show encrypted buckets with versioning enabled')
        print('  python invoke_agent.py Find Python lambda functions in VPC')
        print('  python invoke_agent.py List active DynamoDB tables with streams')
        sys.exit(1)
    
    # Get the prompt from command line arguments
    user_prompt = " ".join(sys.argv[1:])
    
    # Check if AGENT_ARN needs to be updated
    if "YOUR_AGENT_ID" in AGENT_ARN:
        print("Please update the AGENT_ARN in invoke_agent.py with your actual agent ARN")
        print("You can find it after running agentcore create or in the AWS console")
        sys.exit(1)
    
    invoke_agent(user_prompt)
