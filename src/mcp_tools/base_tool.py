"""Base MCP Tool implementation."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
import structlog

logger = structlog.get_logger()


class ToolInput(BaseModel):
    """Base input model for MCP tools."""
    pass


class ToolOutput(BaseModel):
    """Base output model for MCP tools."""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def __str__(self) -> str:
        """Format tool output as a readable string."""
        if not self.success:
            return f"Error: {self.error or self.message}"
        
        result = f"{self.message}\n"
        if self.data:
            # Format data in a natural, readable way
            if "buckets" in self.data:
                buckets = self.data.get("buckets", [])
                if buckets:
                    result += "\nS3 Buckets:\n"
                    for bucket in buckets:
                        bucket_name = bucket.get('name', bucket.get('Name', 'Unknown'))
                        region_info = bucket.get('region', bucket.get('Region', 'Unknown'))
                        result += f"  • {bucket_name} (Region: {region_info})\n"
                        
                        # Add optional details
                        details = []
                        if 'versioning' in bucket:
                            details.append(f"Versioning: {bucket['versioning']}")
                        if 'encryption' in bucket:
                            details.append(f"Encryption: {bucket['encryption']}")
                        if 'public_access' in bucket:
                            details.append(f"Public Access: {bucket['public_access']}")
                        if 'tags' in bucket:
                            tag_str = ', '.join([f"{k}={v}" for k, v in bucket['tags'].items()])
                            details.append(f"Tags: {tag_str}")
                        if 'creation_date' in bucket:
                            details.append(f"Created: {bucket['creation_date']}")
                        
                        if details:
                            result += f"    {' | '.join(details)}\n"
            elif "functions" in self.data:
                functions = self.data.get("functions", [])
                if functions:
                    result += "\nLambda Functions:\n"
                    for func in functions:
                        func_name = func.get('function_name', func.get('FunctionName', 'Unknown'))
                        runtime = func.get('runtime', func.get('Runtime', 'Unknown'))
                        memory = func.get('memory_size', func.get('MemorySize', 0))
                        timeout = func.get('timeout', func.get('Timeout', 0))
                        result += f"  • {func_name}\n"
                        result += f"    Runtime: {runtime} | Memory: {memory}MB | Timeout: {timeout}s\n"
                        
                        # Add optional details
                        if 'vpc_id' in func:
                            result += f"    VPC: {func['vpc_id']}"
                            if 'subnets' in func:
                                result += f" ({func['subnets']} subnets)"
                            result += "\n"
                        if 'env_vars_count' in func:
                            result += f"    Environment Variables: {func['env_vars_count']}\n"
                        if 'tags' in func:
                            tag_str = ', '.join([f"{k}={v}" for k, v in func['tags'].items()])
                            result += f"    Tags: {tag_str}\n"
            elif "tables" in self.data:
                tables = self.data.get("tables", [])
                if tables:
                    result += "\nDynamoDB Tables:\n"
                    for table in tables:
                        table_name = table.get('table_name', table.get('TableName', table.get('name', 'Unknown')))
                        status = table.get('status', table.get('Status', 'Unknown'))
                        result += f"  • {table_name} (Status: {status})\n"
                        
                        # Add optional details
                        details = []
                        if 'billing_mode' in table:
                            details.append(f"Billing: {table['billing_mode']}")
                        if 'item_count' in table:
                            details.append(f"Items: {table['item_count']:,}")
                        if 'partition_key' in table:
                            key_info = f"PK: {table['partition_key']}"
                            if 'sort_key' in table:
                                key_info += f", SK: {table['sort_key']}"
                            details.append(key_info)
                        if 'stream_view_type' in table:
                            details.append(f"Stream: {table['stream_view_type']}")
                        
                        if details:
                            result += f"    {' | '.join(details)}\n"
                        
                        if 'tags' in table:
                            tag_str = ', '.join([f"{k}={v}" for k, v in table['tags'].items()])
                            result += f"    Tags: {tag_str}\n"
            else:
                # For other data types, format key-value pairs
                result += "\nDetails:\n"
                for key, value in self.data.items():
                    if key != "count":
                        result += f"  {key}: {value}\n"
        return result


class BaseMCPTool(ABC):
    """Base class for all MCP tools."""

    def __init__(self, name: str, description: str):
        """Initialize the tool.
        
        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description
        self.logger = logger.bind(tool=name)

    @abstractmethod
    async def execute(self, input_data: ToolInput) -> ToolOutput:
        """Execute the tool.
        
        Args:
            input_data: Tool input parameters
            
        Returns:
            Tool execution result
        """
        pass

    def validate_input(self, input_data: Dict[str, Any]) -> ToolInput:
        """Validate and parse input data.
        
        Args:
            input_data: Raw input data
            
        Returns:
            Validated input model
        """
        try:
            return self.input_model(**input_data)
        except Exception as e:
            self.logger.error("input_validation_failed", error=str(e))
            raise ValueError(f"Invalid input: {str(e)}")

    @property
    @abstractmethod
    def input_model(self) -> type[ToolInput]:
        """Return the input model class."""
        pass

    def log_execution(self, action: str, **kwargs: Any) -> None:
        """Log tool execution.
        
        Args:
            action: Action being performed
            **kwargs: Additional context
        """
        self.logger.info("tool_execution", action=action, **kwargs)

    def handle_error(self, error: Exception, context: str) -> ToolOutput:
        """Handle tool execution errors.
        
        Args:
            error: The error that occurred
            context: Context about where the error occurred
            
        Returns:
            Error output
        """
        self.logger.error("tool_error", context=context, error=str(error))
        return ToolOutput(
            success=False,
            message=f"Error in {context}",
            error=str(error)
        )
