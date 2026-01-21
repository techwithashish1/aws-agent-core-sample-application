"""MCP Tools module."""

from .base_tool import BaseMCPTool, ToolInput, ToolOutput
from .s3_tools import (
    CreateS3BucketTool,
    ListS3BucketsTool,
    DeleteS3BucketTool,
    GetS3BucketInfoTool,
)
from .lambda_tools import (
    CreateLambdaFunctionTool,
    ListLambdaFunctionsTool,
    UpdateLambdaConfigTool,
    DeleteLambdaFunctionTool,
    GetLambdaFunctionInfoTool,
)
from .dynamodb_tools import (
    CreateDynamoDBTableTool,
    ListDynamoDBTablesTool,
    DescribeDynamoDBTableTool,
    DeleteDynamoDBTableTool,
    UpdateDynamoDBTableTool,
)

__all__ = [
    # Base
    "BaseMCPTool",
    "ToolInput",
    "ToolOutput",
    # S3
    "CreateS3BucketTool",
    "ListS3BucketsTool",
    "DeleteS3BucketTool",
    "GetS3BucketInfoTool",
    # Lambda
    "CreateLambdaFunctionTool",
    "ListLambdaFunctionsTool",
    "UpdateLambdaConfigTool",
    "DeleteLambdaFunctionTool",
    "GetLambdaFunctionInfoTool",
    # DynamoDB
    "CreateDynamoDBTableTool",
    "ListDynamoDBTablesTool",
    "DescribeDynamoDBTableTool",
    "DeleteDynamoDBTableTool",
    "UpdateDynamoDBTableTool",
]
