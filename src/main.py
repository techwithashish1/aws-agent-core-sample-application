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
    
    # Show memory status
    session_info = agent.get_session_info()
    if session_info.get("memory_enabled"):
        print(f"Memory enabled - Session: {session_info.get('session_id')}")
    else:
        print("Memory: disabled (set MEMORY_ID to enable)")
    
    # Interactive mode
    print("\nEnter commands or type 'quit' to exit")
    print("Type 'new session' to start a fresh memory session")
    print("Type 'session info' to view memory session details\n")
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            # Handle special commands
            if user_input.lower() == 'new session':
                new_session_id = agent.new_session()
                if new_session_id:
                    print(f"Started new session: {new_session_id}")
                else:
                    print("Memory is not enabled.")
                continue
            
            if user_input.lower() == 'session info':
                info = agent.get_session_info()
                print(f"Memory Info: {info}")
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
