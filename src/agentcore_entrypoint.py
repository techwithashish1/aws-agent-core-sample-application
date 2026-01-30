"""
AWS Bedrock AgentCore Runtime Entrypoint for Langgraph Agent.

This module provides the entrypoint for deploying the AWS Resource Manager
agent to AWS Bedrock AgentCore Runtime. It follows AWS best practices for
Langgraph integration with AgentCore.

Reference: https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/langgraph
"""

import asyncio
from typing import Dict, Any
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import structlog

from agent import AWSResourceAgent
from utils import setup_logging
from config import settings

# Setup logging for AgentCore runtime
setup_logging(
    log_level=settings.log_level,
    log_format=settings.log_format
)

logger = structlog.get_logger()

# Initialize BedrockAgentCore application
app = BedrockAgentCoreApp()

# Initialize the agent (singleton pattern for reuse across invocations)
agent = None


def get_agent() -> AWSResourceAgent:
    """Get or create the agent instance (singleton pattern).
    
    Returns:
        AWSResourceAgent: The agent instance
    """
    global agent
    if agent is None:
        logger.info(
            "initializing_agent",
            agent_name=settings.agent_name,
            model=settings.bedrock_model_id,
            region=settings.bedrock_region
        )
        agent = AWSResourceAgent()
    return agent


@app.entrypoint
def agent_invocation(payload: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AgentCore entrypoint for processing requests.
    
    This function is called by the AgentCore runtime for each agent invocation.
    It processes the incoming payload, executes the agent logic, and returns
    the response.
    
    Args:
        payload: The input payload containing:
            - prompt (str): The user's natural language command
            - session_id (str, optional): Session identifier for context
            - parameters (dict, optional): Additional parameters
        context: The AgentCore context object containing:
            - request_id: Unique request identifier
            - invocation_time: Timestamp of invocation
            - runtime_config: Runtime configuration
    
    Returns:
        dict: Response containing:
            - result (str): The agent's response
            - success (bool): Whether the operation succeeded
            - metadata (dict): Additional information about execution
    
    Example payload:
        {
            "prompt": "List all S3 buckets in my account",
            "session_id": "session-123",
            "parameters": {"verbose": true}
        }
    
    Example response:
        {
            "result": "Found 5 S3 buckets: bucket1, bucket2, ...",
            "success": true,
            "metadata": {
                "model": "anthropic.claude-3-sonnet-20240229-v1:0",
                "request_id": "req-123",
                "execution_time_ms": 1250
            }
        }
    """
    import time
    start_time = time.time()
    
    # Extract prompt from payload
    prompt = payload.get("prompt", payload.get("input", ""))
    session_id = payload.get("session_id", "default")
    
    if not prompt:
        logger.warning("no_prompt_found", payload=payload)
        return {
            "result": "No prompt found in input payload",
            "success": False,
            "metadata": {
                "error": "Missing prompt in payload",
                "request_id": getattr(context, 'request_id', 'unknown')
            }
        }
    
    logger.info(
        "agent_invocation_started",
        prompt=prompt,
        session_id=session_id,
        request_id=getattr(context, 'request_id', 'unknown')
    )
    
    try:
        # Get agent instance
        aws_agent = get_agent()
        
        # Execute agent (using asyncio since our agent is async)
        result = asyncio.run(aws_agent.execute(prompt))
        
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        logger.info(
            "agent_invocation_completed",
            success=True,
            execution_time_ms=execution_time,
            request_id=getattr(context, 'request_id', 'unknown')
        )
        
        return {
            "result": result,
            "success": True,
            "metadata": {
                "model": settings.bedrock_model_id,
                "region": settings.bedrock_region,
                "request_id": getattr(context, 'request_id', 'unknown'),
                "execution_time_ms": round(execution_time, 2),
                "session_id": session_id
            }
        }
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        
        logger.error(
            "agent_invocation_failed",
            error=str(e),
            error_type=type(e).__name__,
            execution_time_ms=execution_time,
            request_id=getattr(context, 'request_id', 'unknown')
        )
        
        return {
            "result": f"Error executing agent: {str(e)}",
            "success": False,
            "metadata": {
                "error": str(e),
                "error_type": type(e).__name__,
                "model": settings.bedrock_model_id,
                "request_id": getattr(context, 'request_id', 'unknown'),
                "execution_time_ms": round(execution_time, 2)
            }
        }


if __name__ == "__main__":
    """
    Run the AgentCore application.
    
    This starts the AgentCore runtime server which listens for invocations
    from the AWS Bedrock AgentCore service.
    
    Usage:
        python agentcore_entrypoint.py
    
    Or with AgentCore CLI:
        agentcore launch -e agentcore_entrypoint.py
    """
    logger.info(
        "starting_agentcore_runtime",
        agent_name=settings.agent_name,
        model=settings.bedrock_model_id,
        region=settings.bedrock_region
    )
    
    # Run the AgentCore application
    app.run()
