"""Lambda MCP Tools for function management."""

from typing import Dict, Any, Optional, List
from pydantic import Field
import boto3
import json
import base64
from botocore.exceptions import ClientError

from .base_tool import BaseMCPTool, ToolInput, ToolOutput
from config import settings


class CreateLambdaFunctionInput(ToolInput):
    """Input for creating a Lambda function."""
    function_name: str = Field(..., description="Name of the Lambda function")
    runtime: str = Field(..., description="Runtime environment (e.g., python3.11, nodejs20.x)")
    handler: str = Field(..., description="Handler function (e.g., index.handler)")
    role_arn: str = Field(..., description="IAM role ARN for the function")
    code_zip_base64: Optional[str] = Field(default=None, description="Base64 encoded ZIP file")
    s3_bucket: Optional[str] = Field(default=None, description="S3 bucket containing code")
    s3_key: Optional[str] = Field(default=None, description="S3 key for code ZIP")
    memory_size: int = Field(default=128, description="Memory size in MB")
    timeout: int = Field(default=30, description="Timeout in seconds")
    environment_variables: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags for the function")


class CreateLambdaFunctionTool(BaseMCPTool):
    """Tool to create Lambda functions."""

    def __init__(self):
        super().__init__(
            name="create_lambda_function",
            description="Create a Lambda function with specified configuration"
        )
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return CreateLambdaFunctionInput

    async def execute(self, input_data: CreateLambdaFunctionInput) -> ToolOutput:
        """Execute Lambda function creation.
        
        Args:
            input_data: Function creation parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("create_lambda", function_name=input_data.function_name)

            # Prepare code configuration
            code_config: Dict[str, Any] = {}
            if input_data.code_zip_base64:
                code_config['ZipFile'] = base64.b64decode(input_data.code_zip_base64)
            elif input_data.s3_bucket and input_data.s3_key:
                code_config['S3Bucket'] = input_data.s3_bucket
                code_config['S3Key'] = input_data.s3_key
            else:
                return ToolOutput(
                    success=False,
                    message="Either code_zip_base64 or s3_bucket/s3_key must be provided",
                    error="Missing code configuration"
                )

            # Create function
            create_params = {
                'FunctionName': input_data.function_name,
                'Runtime': input_data.runtime,
                'Role': input_data.role_arn,
                'Handler': input_data.handler,
                'Code': code_config,
                'MemorySize': input_data.memory_size,
                'Timeout': input_data.timeout,
            }

            if input_data.environment_variables:
                create_params['Environment'] = {
                    'Variables': input_data.environment_variables
                }

            if input_data.tags:
                create_params['Tags'] = input_data.tags

            response = self.lambda_client.create_function(**create_params)

            return ToolOutput(
                success=True,
                message=f"Lambda function '{input_data.function_name}' created successfully",
                data={
                    "function_name": response['FunctionName'],
                    "function_arn": response['FunctionArn'],
                    "runtime": response['Runtime'],
                    "memory_size": response['MemorySize'],
                    "timeout": response['Timeout']
                }
            )

        except ClientError as e:
            return self.handle_error(e, "create_lambda_function")
        except Exception as e:
            return self.handle_error(e, "create_lambda_function")


class ListLambdaFunctionsInput(ToolInput):
    """Input for listing Lambda functions."""
    prefix: Optional[str] = Field(default=None, description="Filter functions by name prefix")
    runtime: Optional[str] = Field(
        default=None,
        description="Filter by runtime. Examples: 'python3.12', 'nodejs20.x', 'java17', 'python' (matches all Python versions). Use when user asks about specific runtime."
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Filter functions by name pattern (case-insensitive substring match). Example: 'prod', 'api', 'processor'. Use when user asks for functions with specific names."
    )
    min_memory: Optional[int] = Field(
        default=None,
        description="Filter functions with memory >= this value (in MB). Example: 512, 1024. Use when user asks about memory configuration."
    )
    max_memory: Optional[int] = Field(
        default=None,
        description="Filter functions with memory <= this value (in MB). Example: 512, 1024. Use when user asks about memory configuration."
    )
    min_timeout: Optional[int] = Field(
        default=None,
        description="Filter functions with timeout >= this value (in seconds). Example: 30, 60. Use when user asks about timeout configuration."
    )
    max_timeout: Optional[int] = Field(
        default=None,
        description="Filter functions with timeout <= this value (in seconds). Example: 30, 60. Use when user asks about timeout configuration."
    )
    vpc_configured: Optional[bool] = Field(
        default=None,
        description="Filter by VPC configuration. True = only functions in VPC, False = only functions not in VPC. Use when user asks about VPC."
    )
    has_environment_vars: Optional[bool] = Field(
        default=None,
        description="Filter by environment variables presence. True = only functions with env vars, False = only functions without. Use when user asks about environment variables."
    )
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter functions by tags. Example: {'Environment': 'Production', 'Team': 'Backend'}. Use when user asks for tagged functions."
    )
    max_items: int = Field(default=100, description="Maximum number of functions to return")


class ListLambdaFunctionsTool(BaseMCPTool):
    """Tool to list Lambda functions."""

    def __init__(self):
        super().__init__(
            name="list_lambda_functions",
            description=(
                "List Lambda functions with comprehensive filtering. "
                "ALWAYS use appropriate filters when user requests specific criteria: "
                "runtime (e.g., 'python', 'nodejs'), name_pattern (substring match), min_memory/max_memory (MB), "
                "min_timeout/max_timeout (seconds), vpc_configured (True/False), has_environment_vars (True/False), "
                "tags (dict). Multiple filters can be combined."
            )
        )
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return ListLambdaFunctionsInput

    async def execute(self, input_data: ListLambdaFunctionsInput) -> ToolOutput:
        """Execute Lambda function listing.
        
        Args:
            input_data: Listing parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("list_lambdas")

            # Get all functions using paginator
            paginator = self.lambda_client.get_paginator('list_functions')
            all_functions = []
            for page in paginator.paginate(MaxItems=input_data.max_items):
                all_functions.extend(page.get('Functions', []))

            filtered_functions = []
            
            for func in all_functions:
                function_name = func['FunctionName']
                
                # Apply prefix filter
                if input_data.prefix and not function_name.startswith(input_data.prefix):
                    continue
                
                # Apply name pattern filter
                if input_data.name_pattern and input_data.name_pattern.lower() not in function_name.lower():
                    continue
                
                # Apply runtime filter
                if input_data.runtime:
                    func_runtime = func.get('Runtime', '')
                    if input_data.runtime.lower() not in func_runtime.lower():
                        continue
                
                # Apply memory filters
                memory_size = func.get('MemorySize', 0)
                if input_data.min_memory and memory_size < input_data.min_memory:
                    continue
                if input_data.max_memory and memory_size > input_data.max_memory:
                    continue
                
                # Apply timeout filters
                timeout = func.get('Timeout', 0)
                if input_data.min_timeout and timeout < input_data.min_timeout:
                    continue
                if input_data.max_timeout and timeout > input_data.max_timeout:
                    continue
                
                # Apply VPC filter
                if input_data.vpc_configured is not None:
                    has_vpc = bool(func.get('VpcConfig', {}).get('VpcId'))
                    if has_vpc != input_data.vpc_configured:
                        continue
                
                # Apply environment variables filter
                if input_data.has_environment_vars is not None:
                    has_env = bool(func.get('Environment', {}).get('Variables'))
                    if has_env != input_data.has_environment_vars:
                        continue
                
                # Apply tags filter
                function_tags = None
                if input_data.tags:
                    try:
                        function_arn = func['FunctionArn']
                        tags_response = self.lambda_client.list_tags(Resource=function_arn)
                        function_tags = tags_response.get('Tags', {})
                        if not all(function_tags.get(k) == v for k, v in input_data.tags.items()):
                            continue
                    except Exception as e:
                        self.logger.warning(f"Could not get tags for function {function_name}: {str(e)}")
                        continue
                
                # Build function info
                function_info = {
                    "function_name": function_name,
                    "runtime": func.get('Runtime', 'Unknown'),
                    "memory_size": memory_size,
                    "timeout": timeout,
                    "handler": func.get('Handler', 'Unknown'),
                    "last_modified": func.get('LastModified', 'Unknown'),
                    "code_size": func.get('CodeSize', 0)
                }
                
                # Add VPC info if configured
                vpc_config = func.get('VpcConfig', {})
                if vpc_config.get('VpcId'):
                    function_info['vpc_id'] = vpc_config['VpcId']
                    function_info['subnets'] = len(vpc_config.get('SubnetIds', []))
                
                # Add environment variables info
                env_vars = func.get('Environment', {}).get('Variables', {})
                if env_vars:
                    function_info['env_vars_count'] = len(env_vars)
                
                # Add tags if checked
                if function_tags:
                    function_info['tags'] = function_tags
                
                filtered_functions.append(function_info)

            # Build message with filters
            filters_applied = []
            if input_data.prefix:
                filters_applied.append(f"prefix: '{input_data.prefix}'")
            if input_data.runtime:
                filters_applied.append(f"runtime: {input_data.runtime}")
            if input_data.name_pattern:
                filters_applied.append(f"name pattern: '{input_data.name_pattern}'")
            if input_data.min_memory:
                filters_applied.append(f"min memory: {input_data.min_memory}MB")
            if input_data.max_memory:
                filters_applied.append(f"max memory: {input_data.max_memory}MB")
            if input_data.min_timeout:
                filters_applied.append(f"min timeout: {input_data.min_timeout}s")
            if input_data.max_timeout:
                filters_applied.append(f"max timeout: {input_data.max_timeout}s")
            if input_data.vpc_configured is not None:
                filters_applied.append(f"VPC: {'configured' if input_data.vpc_configured else 'not configured'}")
            if input_data.has_environment_vars is not None:
                filters_applied.append(f"env vars: {'present' if input_data.has_environment_vars else 'absent'}")
            if input_data.tags:
                filters_applied.append(f"tags: {input_data.tags}")

            message = f"Found {len(filtered_functions)} Lambda function(s)"
            if filters_applied:
                message += f" (Filters: {', '.join(filters_applied)})"

            return ToolOutput(
                success=True,
                message=message,
                data={"functions": filtered_functions, "count": len(filtered_functions)}
            )

        except ClientError as e:
            return self.handle_error(e, "list_lambda_functions")
        except Exception as e:
            return self.handle_error(e, "list_lambda_functions")


class UpdateLambdaConfigInput(ToolInput):
    """Input for updating Lambda function configuration."""
    function_name: str = Field(..., description="Name of the Lambda function")
    memory_size: Optional[int] = Field(default=None, description="Memory size in MB")
    timeout: Optional[int] = Field(default=None, description="Timeout in seconds")
    environment_variables: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")


class UpdateLambdaConfigTool(BaseMCPTool):
    """Tool to update Lambda function configuration."""

    def __init__(self):
        super().__init__(
            name="update_lambda_config",
            description="Update Lambda function configuration"
        )
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return UpdateLambdaConfigInput

    async def execute(self, input_data: UpdateLambdaConfigInput) -> ToolOutput:
        """Execute Lambda configuration update.
        
        Args:
            input_data: Update parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("update_lambda_config", function_name=input_data.function_name)

            update_params: Dict[str, Any] = {'FunctionName': input_data.function_name}

            if input_data.memory_size is not None:
                update_params['MemorySize'] = input_data.memory_size
            
            if input_data.timeout is not None:
                update_params['Timeout'] = input_data.timeout
            
            if input_data.environment_variables is not None:
                update_params['Environment'] = {
                    'Variables': input_data.environment_variables
                }

            response = self.lambda_client.update_function_configuration(**update_params)

            return ToolOutput(
                success=True,
                message=f"Lambda function '{input_data.function_name}' configuration updated",
                data={
                    "function_name": response['FunctionName'],
                    "memory_size": response['MemorySize'],
                    "timeout": response['Timeout']
                }
            )

        except ClientError as e:
            return self.handle_error(e, "update_lambda_config")
        except Exception as e:
            return self.handle_error(e, "update_lambda_config")


class DeleteLambdaFunctionInput(ToolInput):
    """Input for deleting a Lambda function."""
    function_name: str = Field(..., description="Name of the Lambda function to delete")


class DeleteLambdaFunctionTool(BaseMCPTool):
    """Tool to delete Lambda functions."""

    def __init__(self):
        super().__init__(
            name="delete_lambda_function",
            description="Delete a Lambda function"
        )
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return DeleteLambdaFunctionInput

    async def execute(self, input_data: DeleteLambdaFunctionInput) -> ToolOutput:
        """Execute Lambda function deletion.
        
        Args:
            input_data: Deletion parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("delete_lambda", function_name=input_data.function_name)

            self.lambda_client.delete_function(FunctionName=input_data.function_name)

            return ToolOutput(
                success=True,
                message=f"Lambda function '{input_data.function_name}' deleted successfully",
                data={"function_name": input_data.function_name}
            )

        except ClientError as e:
            return self.handle_error(e, "delete_lambda_function")
        except Exception as e:
            return self.handle_error(e, "delete_lambda_function")


class GetLambdaFunctionInfoInput(ToolInput):
    """Input for getting Lambda function information."""
    function_name: str = Field(..., description="Name of the Lambda function")


class GetLambdaFunctionInfoTool(BaseMCPTool):
    """Tool to get Lambda function information."""

    def __init__(self):
        super().__init__(
            name="get_lambda_function_info",
            description="Get detailed information about a Lambda function"
        )
        self.lambda_client = boto3.client('lambda', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return GetLambdaFunctionInfoInput

    async def execute(self, input_data: GetLambdaFunctionInfoInput) -> ToolOutput:
        """Execute Lambda function info retrieval.
        
        Args:
            input_data: Info retrieval parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("get_lambda_info", function_name=input_data.function_name)

            response = self.lambda_client.get_function(FunctionName=input_data.function_name)
            config = response['Configuration']

            info = {
                "function_name": config['FunctionName'],
                "function_arn": config['FunctionArn'],
                "runtime": config['Runtime'],
                "role": config['Role'],
                "handler": config['Handler'],
                "memory_size": config['MemorySize'],
                "timeout": config['Timeout'],
                "last_modified": config['LastModified'],
                "code_size": config['CodeSize'],
                "environment_variables": config.get('Environment', {}).get('Variables', {})
            }

            return ToolOutput(
                success=True,
                message=f"Retrieved information for Lambda function '{input_data.function_name}'",
                data=info
            )

        except ClientError as e:
            return self.handle_error(e, "get_lambda_function_info")
        except Exception as e:
            return self.handle_error(e, "get_lambda_function_info")
