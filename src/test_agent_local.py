"""
Local test script for AWS Resource Manager Agent with AgentCore Gateway integration.

Usage:
    python test_agent_local.py
"""

import os
import sys

# Set SSL_VERIFY for corporate environments
os.environ['SSL_VERIFY'] = 'false'

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent import AWSResourceAgent


def main():
    print("=" * 70)
    print("AWS Resource Manager Agent - Local Test")
    print("=" * 70)
    
    print("\nInitializing agent with gateway tools...")
    try:
        agent = AWSResourceAgent(include_gateway_tools=True)
        print(f"Agent initialized with {len(agent.tools)} tools:")
        for tool in agent.tools:
            print(f"  - {tool.name}")
    except Exception as e:
        print(f"Failed to initialize agent: {e}")
        return
    
    print("\n" + "=" * 70)
    print("Interactive Mode - Type 'quit' to exit")
    print("=" * 70)
    
    # Sample prompts to try
    print("\nSample prompts to try:")
    print("  1. Show me S3 bucket metrics")
    print("  2. Get Lambda function metrics")
    print("  3. What are the DynamoDB table metrics?")
    print("  4. List all S3 buckets")
    print("  5. List Lambda functions")
    print()
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            print("\nAgent is thinking...")
            response = agent.execute_sync(user_input)
            print(f"\nAgent: {response}")
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()
