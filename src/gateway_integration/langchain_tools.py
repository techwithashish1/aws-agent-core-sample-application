"""
LangChain Tool Wrappers for AgentCore Gateway MCP Tools.
"""

import json
from typing import List, Dict, Any, Optional, Type
from langchain_core.tools import BaseTool, ToolException
from pydantic import BaseModel, Field, create_model

from .mcp_client import MCPGatewayClient, MCPTool


def json_schema_to_pydantic(schema: Dict[str, Any], model_name: str) -> Type[BaseModel]:
    """Convert JSON Schema to Pydantic model."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    fields = {}
    for prop_name, prop_schema in properties.items():
        prop_type = prop_schema.get("type", "string")
        description = prop_schema.get("description", "")
        
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        python_type = type_mapping.get(prop_type, str)
        
        if prop_name in required:
            fields[prop_name] = (python_type, Field(description=description))
        else:
            fields[prop_name] = (Optional[python_type], Field(default=None, description=description))
    
    if not fields:
        fields["dummy"] = (Optional[str], Field(default=None, description="Placeholder"))
    
    return create_model(model_name, **fields)


class GatewayTool(BaseTool):
    """LangChain tool wrapper for an MCP Gateway tool."""
    
    name: str
    description: str
    args_schema: Type[BaseModel]
    mcp_client: Any = None
    mcp_tool_name: str = ""
    
    class Config:
        arbitrary_types_allowed = True
    
    def _run(self, **kwargs) -> str:
        """Execute the tool synchronously."""
        try:
            arguments = {k: v for k, v in kwargs.items() if v is not None and k != "dummy"}
            result = self.mcp_client.call_tool(self.mcp_tool_name, arguments)
            if isinstance(result, dict):
                return json.dumps(result, indent=2)
            return str(result)
        except Exception as e:
            raise ToolException(f"Error calling gateway tool '{self.mcp_tool_name}': {str(e)}")
    
    async def _arun(self, **kwargs) -> str:
        """Execute the tool asynchronously."""
        return self._run(**kwargs)


def create_gateway_tools(mcp_client: MCPGatewayClient) -> List[BaseTool]:
    """Create LangChain tools from MCP Gateway tools."""
    if not mcp_client.initialize():
        raise Exception("Failed to initialize MCP connection")
    
    mcp_tools = mcp_client.list_tools()
    langchain_tools = []
    
    for mcp_tool in mcp_tools:
        model_name = f"{mcp_tool.name.replace('-', '_').replace(' ', '_')}Args"
        args_schema = json_schema_to_pydantic(mcp_tool.input_schema, model_name)
        
        tool = GatewayTool(
            name=mcp_tool.name,
            description=mcp_tool.description or f"Tool: {mcp_tool.name}",
            args_schema=args_schema,
            mcp_client=mcp_client,
            mcp_tool_name=mcp_tool.name
        )
        langchain_tools.append(tool)
    
    return langchain_tools
