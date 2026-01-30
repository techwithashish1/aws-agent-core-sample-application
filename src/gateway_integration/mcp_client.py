"""
MCP Client for AgentCore Gateway.
"""

import os
import json
import base64
import requests
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# SSL verification setting (for corporate environments with SSL proxies)
SSL_VERIFY = os.environ.get('SSL_VERIFY', 'true').lower() != 'false'


@dataclass
class MCPTool:
    """Represents an MCP tool from the gateway."""
    name: str
    description: str
    input_schema: Dict[str, Any]


class MCPGatewayClient:
    """Client for connecting to AgentCore Gateway via MCP protocol."""
    
    def __init__(
        self,
        gateway_url: str,
        cognito_token_url: str,
        client_id: str,
        client_secret: str,
        scope: str
    ):
        self.gateway_url = gateway_url
        self.cognito_token_url = cognito_token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self._access_token: Optional[str] = None
        self._tools: List[MCPTool] = []
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token from Cognito."""
        if self._access_token:
            return self._access_token
        
        credentials = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {credentials}"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": self.scope
        }
        
        response = requests.post(
            self.cognito_token_url,
            headers=headers,
            data=data,
            verify=SSL_VERIFY
        )
        response.raise_for_status()
        
        self._access_token = response.json()["access_token"]
        return self._access_token
    
    def _make_mcp_request(self, method: str, params: Optional[Dict] = None) -> Dict:
        """Make an MCP JSON-RPC request to the gateway."""
        token = self._get_access_token()
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method
        }
        if params:
            payload["params"] = params
        
        response = requests.post(
            self.gateway_url,
            headers=headers,
            json=payload,
            verify=SSL_VERIFY
        )
        response.raise_for_status()
        
        return response.json()
    
    def initialize(self) -> bool:
        """Initialize the MCP connection."""
        try:
            result = self._make_mcp_request("initialize", {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "aws-resource-manager-agent",
                    "version": "1.0.0"
                }
            })
            return "result" in result
        except Exception as e:
            print(f"Failed to initialize MCP connection: {e}")
            return False
    
    def list_tools(self) -> List[MCPTool]:
        """List available tools from the gateway."""
        if self._tools:
            return self._tools
        
        result = self._make_mcp_request("tools/list")
        
        if "result" in result and "tools" in result["result"]:
            self._tools = [
                MCPTool(
                    name=tool["name"],
                    description=tool.get("description", ""),
                    input_schema=tool.get("inputSchema", {})
                )
                for tool in result["result"]["tools"]
            ]
        
        return self._tools
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool on the gateway."""
        result = self._make_mcp_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        
        if "result" in result:
            content = result["result"].get("content", [])
            if content and len(content) > 0:
                text_content = content[0].get("text", "")
                try:
                    return json.loads(text_content)
                except json.JSONDecodeError:
                    return text_content
        
        if "error" in result:
            raise Exception(f"Tool call failed: {result['error']}")
        
        return result
    
    @classmethod
    def from_config(cls, config_path: str) -> "MCPGatewayClient":
        """Create client from saved gateway configuration."""
        with open(config_path, "r") as f:
            config = json.load(f)
        
        gateway_url = config["gateway"]["url"]
        cognito = config["cognito"]
        region = config.get("region", "us-east-1")
        
        # Build token URL from user_pool_id
        user_pool_id = cognito["user_pool_id"]
        # Domain is typically user_pool_id with underscores removed and lowercased
        domain = user_pool_id.lower().replace("_", "")
        
        return cls(
            gateway_url=gateway_url,
            cognito_token_url=f"https://{domain}.auth.{region}.amazoncognito.com/oauth2/token",
            client_id=cognito["client_id"],
            client_secret=cognito["client_secret"],
            scope=cognito["scope_string"]
        )
