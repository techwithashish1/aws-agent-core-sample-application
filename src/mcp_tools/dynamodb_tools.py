"""DynamoDB MCP Tools for table management (no data operations)."""

from typing import Dict, Any, Optional, List
from pydantic import Field
import boto3
from botocore.exceptions import ClientError

from .base_tool import BaseMCPTool, ToolInput, ToolOutput
from config import settings


class CreateDynamoDBTableInput(ToolInput):
    """Input for creating a DynamoDB table."""
    table_name: str = Field(..., description="Name of the DynamoDB table")
    partition_key: str = Field(..., description="Partition key attribute name")
    partition_key_type: str = Field(default="S", description="Partition key type (S, N, B)")
    sort_key: Optional[str] = Field(default=None, description="Sort key attribute name")
    sort_key_type: Optional[str] = Field(default="S", description="Sort key type (S, N, B)")
    billing_mode: str = Field(default="PAY_PER_REQUEST", description="PROVISIONED or PAY_PER_REQUEST")
    read_capacity: Optional[int] = Field(default=5, description="Read capacity units (for PROVISIONED)")
    write_capacity: Optional[int] = Field(default=5, description="Write capacity units (for PROVISIONED)")
    stream_enabled: bool = Field(default=False, description="Enable DynamoDB streams")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags for the table")


class CreateDynamoDBTableTool(BaseMCPTool):
    """Tool to create DynamoDB tables."""

    def __init__(self):
        super().__init__(
            name="create_dynamodb_table",
            description="Create a DynamoDB table with specified configuration"
        )
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return CreateDynamoDBTableInput

    async def execute(self, input_data: CreateDynamoDBTableInput) -> ToolOutput:
        """Execute DynamoDB table creation.
        
        Args:
            input_data: Table creation parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("create_dynamodb_table", table_name=input_data.table_name)

            # Define key schema
            key_schema = [
                {'AttributeName': input_data.partition_key, 'KeyType': 'HASH'}
            ]
            
            attribute_definitions = [
                {'AttributeName': input_data.partition_key, 'AttributeType': input_data.partition_key_type}
            ]

            if input_data.sort_key:
                key_schema.append({'AttributeName': input_data.sort_key, 'KeyType': 'RANGE'})
                attribute_definitions.append({
                    'AttributeName': input_data.sort_key,
                    'AttributeType': input_data.sort_key_type or 'S'
                })

            # Prepare create parameters
            create_params: Dict[str, Any] = {
                'TableName': input_data.table_name,
                'KeySchema': key_schema,
                'AttributeDefinitions': attribute_definitions,
                'BillingMode': input_data.billing_mode
            }

            # Add provisioned throughput if needed
            if input_data.billing_mode == 'PROVISIONED':
                create_params['ProvisionedThroughput'] = {
                    'ReadCapacityUnits': input_data.read_capacity or 5,
                    'WriteCapacityUnits': input_data.write_capacity or 5
                }

            # Add stream specification if enabled
            if input_data.stream_enabled:
                create_params['StreamSpecification'] = {
                    'StreamEnabled': True,
                    'StreamViewType': 'NEW_AND_OLD_IMAGES'
                }

            # Add tags if provided
            if input_data.tags:
                create_params['Tags'] = [
                    {'Key': k, 'Value': v} for k, v in input_data.tags.items()
                ]

            # Create table
            response = self.dynamodb_client.create_table(**create_params)

            return ToolOutput(
                success=True,
                message=f"DynamoDB table '{input_data.table_name}' creation initiated",
                data={
                    "table_name": response['TableDescription']['TableName'],
                    "table_arn": response['TableDescription']['TableArn'],
                    "table_status": response['TableDescription']['TableStatus'],
                    "partition_key": input_data.partition_key,
                    "sort_key": input_data.sort_key
                }
            )

        except ClientError as e:
            return self.handle_error(e, "create_dynamodb_table")
        except Exception as e:
            return self.handle_error(e, "create_dynamodb_table")


class ListDynamoDBTablesInput(ToolInput):
    """Input for listing DynamoDB tables."""
    name_pattern: Optional[str] = Field(
        default=None,
        description="Filter tables by name pattern (case-insensitive substring match). Example: 'prod', 'user', 'orders'. Use when user asks for tables with specific names."
    )
    billing_mode: Optional[str] = Field(
        default=None,
        description="Filter by billing mode. Values: 'PROVISIONED' or 'PAY_PER_REQUEST'. Use when user asks about on-demand or provisioned tables."
    )
    table_status: Optional[str] = Field(
        default=None,
        description="Filter by table status. Values: 'ACTIVE', 'CREATING', 'UPDATING', 'DELETING'. Use when user asks about table status."
    )
    has_streams: Optional[bool] = Field(
        default=None,
        description="Filter tables with DynamoDB Streams enabled. True = only tables with streams, False = only without streams. Use when user asks about streams."
    )
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter tables by tags. Example: {'Environment': 'Production', 'Team': 'DataTeam'}. Use when user asks for tagged tables."
    )
    limit: int = Field(default=100, description="Maximum number of tables to return")


class ListDynamoDBTablesTool(BaseMCPTool):
    """Tool to list DynamoDB tables."""

    def __init__(self):
        super().__init__(
            name="list_dynamodb_tables",
            description=(
                "List DynamoDB tables with comprehensive filtering. "
                "ALWAYS use appropriate filters when user requests specific criteria: "
                "name_pattern (substring match), billing_mode ('PROVISIONED'/'PAY_PER_REQUEST'), "
                "table_status ('ACTIVE'/'CREATING'/etc), has_streams (True/False), "
                "tags (dict). Multiple filters can be combined."
            )
        )
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return ListDynamoDBTablesInput

    async def execute(self, input_data: ListDynamoDBTablesInput) -> ToolOutput:
        """Execute DynamoDB table listing with comprehensive filtering.
        
        Args:
            input_data: Listing parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("list_dynamodb_tables")

            # Get all table names
            paginator = self.dynamodb_client.get_paginator('list_tables')
            all_table_names = []
            for page in paginator.paginate(PaginationConfig={'MaxItems': input_data.limit}):
                all_table_names.extend(page.get('TableNames', []))
            
            # Apply name pattern filter early
            if input_data.name_pattern:
                all_table_names = [t for t in all_table_names if input_data.name_pattern.lower() in t.lower()]

            filtered_tables = []
            
            for table_name in all_table_names:
                try:
                    # Get detailed table information
                    table_desc = self.dynamodb_client.describe_table(TableName=table_name)
                    table = table_desc['Table']
                    
                    # Apply billing mode filter
                    if input_data.billing_mode:
                        table_billing = table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED')
                        if table_billing != input_data.billing_mode:
                            continue
                    
                    # Apply status filter
                    if input_data.table_status:
                        if table.get('TableStatus') != input_data.table_status:
                            continue
                    
                    # Apply streams filter
                    if input_data.has_streams is not None:
                        stream_spec = table.get('StreamSpecification', {})
                        stream_enabled = stream_spec.get('StreamEnabled', False)
                        if stream_enabled != input_data.has_streams:
                            continue
                    
                    # Apply tags filter
                    table_tags = None
                    if input_data.tags:
                        try:
                            tags_response = self.dynamodb_client.list_tags_of_resource(
                                ResourceArn=table['TableArn']
                            )
                            table_tags = {tag['Key']: tag['Value'] for tag in tags_response.get('Tags', [])}
                            if not all(table_tags.get(k) == v for k, v in input_data.tags.items()):
                                continue
                        except Exception as e:
                            self.logger.warning(f"Could not get tags for table {table_name}: {str(e)}")
                            continue
                    
                    # Build table info
                    table_info = {
                        "table_name": table_name,
                        "status": table.get('TableStatus', 'Unknown'),
                        "item_count": table.get('ItemCount', 0),
                        "size_bytes": table.get('TableSizeBytes', 0),
                        "billing_mode": table.get('BillingModeSummary', {}).get('BillingMode', 'PROVISIONED'),
                        "creation_date": table.get('CreationDateTime', '').isoformat() if table.get('CreationDateTime') else 'Unknown'
                    }
                    
                    # Add key schema
                    key_schema = table.get('KeySchema', [])
                    partition_key = next((k['AttributeName'] for k in key_schema if k['KeyType'] == 'HASH'), None)
                    sort_key = next((k['AttributeName'] for k in key_schema if k['KeyType'] == 'RANGE'), None)
                    if partition_key:
                        table_info['partition_key'] = partition_key
                    if sort_key:
                        table_info['sort_key'] = sort_key
                    
                    # Add stream info
                    stream_spec = table.get('StreamSpecification', {})
                    if stream_spec.get('StreamEnabled'):
                        table_info['stream_view_type'] = stream_spec.get('StreamViewType', 'Unknown')
                    
                    # Add tags if checked
                    if table_tags:
                        table_info['tags'] = table_tags
                    
                    filtered_tables.append(table_info)
                    
                except Exception as e:
                    self.logger.warning(f"Error processing table {table_name}: {str(e)}")
                    continue

            # Build message with filters
            filters_applied = []
            if input_data.name_pattern:
                filters_applied.append(f"name pattern: '{input_data.name_pattern}'")
            if input_data.billing_mode:
                filters_applied.append(f"billing mode: {input_data.billing_mode}")
            if input_data.table_status:
                filters_applied.append(f"status: {input_data.table_status}")
            if input_data.has_streams is not None:
                filters_applied.append(f"streams: {'enabled' if input_data.has_streams else 'disabled'}")
            if input_data.tags:
                filters_applied.append(f"tags: {input_data.tags}")

            message = f"Found {len(filtered_tables)} DynamoDB table(s)"
            if filters_applied:
                message += f" (Filters: {', '.join(filters_applied)})"

            return ToolOutput(
                success=True,
                message=message,
                data={"tables": filtered_tables, "count": len(filtered_tables)}
            )

        except ClientError as e:
            return self.handle_error(e, "list_dynamodb_tables")
        except Exception as e:
            return self.handle_error(e, "list_dynamodb_tables")


class DescribeDynamoDBTableInput(ToolInput):
    """Input for describing a DynamoDB table."""
    table_name: str = Field(..., description="Name of the DynamoDB table")


class DescribeDynamoDBTableTool(BaseMCPTool):
    """Tool to get DynamoDB table information."""

    def __init__(self):
        super().__init__(
            name="describe_dynamodb_table",
            description="Get detailed information about a DynamoDB table"
        )
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return DescribeDynamoDBTableInput

    async def execute(self, input_data: DescribeDynamoDBTableInput) -> ToolOutput:
        """Execute DynamoDB table description.
        
        Args:
            input_data: Description parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("describe_dynamodb_table", table_name=input_data.table_name)

            response = self.dynamodb_client.describe_table(TableName=input_data.table_name)
            table = response['Table']

            info = {
                "table_name": table['TableName'],
                "table_arn": table['TableArn'],
                "table_status": table['TableStatus'],
                "creation_date": table['CreationDateTime'].isoformat(),
                "item_count": table.get('ItemCount', 0),
                "table_size_bytes": table.get('TableSizeBytes', 0),
                "billing_mode": table.get('BillingModeSummary', {}).get('BillingMode', 'UNKNOWN'),
                "key_schema": table['KeySchema'],
                "attribute_definitions": table['AttributeDefinitions']
            }

            # Add provisioned throughput if available
            if 'ProvisionedThroughput' in table:
                info['provisioned_throughput'] = {
                    "read_capacity": table['ProvisionedThroughput'].get('ReadCapacityUnits'),
                    "write_capacity": table['ProvisionedThroughput'].get('WriteCapacityUnits')
                }

            # Add stream info if available
            if 'StreamSpecification' in table:
                info['stream_enabled'] = table['StreamSpecification'].get('StreamEnabled', False)

            return ToolOutput(
                success=True,
                message=f"Retrieved information for DynamoDB table '{input_data.table_name}'",
                data=info
            )

        except ClientError as e:
            return self.handle_error(e, "describe_dynamodb_table")
        except Exception as e:
            return self.handle_error(e, "describe_dynamodb_table")


class DeleteDynamoDBTableInput(ToolInput):
    """Input for deleting a DynamoDB table."""
    table_name: str = Field(..., description="Name of the DynamoDB table to delete")


class DeleteDynamoDBTableTool(BaseMCPTool):
    """Tool to delete DynamoDB tables."""

    def __init__(self):
        super().__init__(
            name="delete_dynamodb_table",
            description="Delete a DynamoDB table"
        )
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return DeleteDynamoDBTableInput

    async def execute(self, input_data: DeleteDynamoDBTableInput) -> ToolOutput:
        """Execute DynamoDB table deletion.
        
        Args:
            input_data: Deletion parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("delete_dynamodb_table", table_name=input_data.table_name)

            response = self.dynamodb_client.delete_table(TableName=input_data.table_name)

            return ToolOutput(
                success=True,
                message=f"DynamoDB table '{input_data.table_name}' deletion initiated",
                data={
                    "table_name": input_data.table_name,
                    "table_status": response['TableDescription']['TableStatus']
                }
            )

        except ClientError as e:
            return self.handle_error(e, "delete_dynamodb_table")
        except Exception as e:
            return self.handle_error(e, "delete_dynamodb_table")


class UpdateDynamoDBTableInput(ToolInput):
    """Input for updating a DynamoDB table."""
    table_name: str = Field(..., description="Name of the DynamoDB table")
    billing_mode: Optional[str] = Field(default=None, description="PROVISIONED or PAY_PER_REQUEST")
    read_capacity: Optional[int] = Field(default=None, description="Read capacity units")
    write_capacity: Optional[int] = Field(default=None, description="Write capacity units")


class UpdateDynamoDBTableTool(BaseMCPTool):
    """Tool to update DynamoDB table configuration."""

    def __init__(self):
        super().__init__(
            name="update_dynamodb_table",
            description="Update DynamoDB table configuration"
        )
        self.dynamodb_client = boto3.client('dynamodb', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return UpdateDynamoDBTableInput

    async def execute(self, input_data: UpdateDynamoDBTableInput) -> ToolOutput:
        """Execute DynamoDB table update.
        
        Args:
            input_data: Update parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("update_dynamodb_table", table_name=input_data.table_name)

            update_params: Dict[str, Any] = {'TableName': input_data.table_name}

            if input_data.billing_mode:
                update_params['BillingMode'] = input_data.billing_mode

            if input_data.read_capacity and input_data.write_capacity:
                update_params['ProvisionedThroughput'] = {
                    'ReadCapacityUnits': input_data.read_capacity,
                    'WriteCapacityUnits': input_data.write_capacity
                }

            response = self.dynamodb_client.update_table(**update_params)

            return ToolOutput(
                success=True,
                message=f"DynamoDB table '{input_data.table_name}' update initiated",
                data={
                    "table_name": input_data.table_name,
                    "table_status": response['TableDescription']['TableStatus']
                }
            )

        except ClientError as e:
            return self.handle_error(e, "update_dynamodb_table")
        except Exception as e:
            return self.handle_error(e, "update_dynamodb_table")
