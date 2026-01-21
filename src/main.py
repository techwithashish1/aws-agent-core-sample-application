"""Main entry point for AWS Resource Manager."""

import asyncio
from typing import Optional
from agent import AWSResourceAgent
from utils import setup_logging
from config import settings
import structlog

logger = structlog.get_logger()


async def main():
    """Main application entry point."""
    # Setup logging
    setup_logging(
        log_level=settings.log_level,
        log_format=settings.log_format
    )
    
    logger.info(
        "starting_aws_resource_manager",
        agent_name=settings.agent_name,
        model=settings.bedrock_model_id
    )
    
    # Initialize agent
    agent = AWSResourceAgent()
    
    # Example usage
    print("AWS Resource Manager - Agentic AI Application")
    
    # Interactive mode
    print("Enter commands or type quit to exit")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Execute command
            response = await agent.execute(user_input)
            print(f"Agent: {response}")
            
        except KeyboardInterrupt:
            print("Goodbye!")
            break
        except Exception as e:
            logger.error("error_in_main_loop", error=str(e))
            print(f"Error: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
