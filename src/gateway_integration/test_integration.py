"""
Test script for AgentCore Gateway integration.
"""

import os
import sys

# Add src directory to path for imports
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, src_dir)

from gateway_integration.mcp_client import MCPGatewayClient
from gateway_integration.langchain_tools import create_gateway_tools


def main():
    config_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "agentcore_gateway",
        "gateway_config.json"
    )
    
    print("=" * 60)
    print("Testing AgentCore Gateway Integration")
    print("=" * 60)
    
    print(f"Loading config from: {config_path}")
    client = MCPGatewayClient.from_config(config_path)
    
    print("Initializing MCP connection...")
    if not client.initialize():
        print("Failed to initialize MCP connection")
        return
    
    print("MCP connection initialized successfully")
    
    print("Listing available tools...")
    tools = client.list_tools()
    print(f"Found {len(tools)} tools:")
    for tool in tools:
        print(f"  - {tool.name}")
    
    print("Creating LangChain tools...")
    lc_tools = create_gateway_tools(client)
    print(f"Created {len(lc_tools)} LangChain tools")
    
    print("Testing S3 metrics tool...")
    for tool in lc_tools:
        if "s3" in tool.name.lower():
            try:
                result = tool.invoke({})
                print(f"Result: {str(result)[:300]}...")
            except Exception as e:
                print(f"Error: {e}")
            break
    
    print("=" * 60)
    print("Test completed")
    print("=" * 60)


if __name__ == "__main__":
    main()
