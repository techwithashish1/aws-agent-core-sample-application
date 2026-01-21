"""Metrics and monitoring tools for AWS resources."""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pydantic import Field
import boto3
from botocore.exceptions import ClientError

from .base_tool import BaseMCPTool, ToolInput, ToolOutput
from config import settings


class GetS3MetricsInput(ToolInput):
    """Input for getting S3 bucket metrics."""
    bucket_name: str = Field(..., description="Name of the S3 bucket")
    days: int = Field(default=7, description="Number of days to retrieve metrics for")


class GetS3MetricsTool(BaseMCPTool):
    """Tool to get S3 bucket metrics from CloudWatch."""

    def __init__(self):
        super().__init__(
            name="get_s3_metrics",
            description="Get CloudWatch metrics for an S3 bucket"
        )
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return GetS3MetricsInput

    async def execute(self, input_data: GetS3MetricsInput) -> ToolOutput:
        """Execute S3 metrics retrieval.
        
        Args:
            input_data: Metrics parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("get_s3_metrics", bucket_name=input_data.bucket_name)

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=input_data.days)

            metrics_data: Dict[str, Any] = {
                "bucket_name": input_data.bucket_name,
                "period_days": input_data.days
            }

            # Get bucket size
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='BucketSizeBytes',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': input_data.bucket_name},
                        {'Name': 'StorageType', 'Value': 'StandardStorage'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )
                if response['Datapoints']:
                    latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics_data['bucket_size_bytes'] = int(latest['Average'])
                    metrics_data['bucket_size_gb'] = round(latest['Average'] / (1024**3), 2)
            except ClientError:
                metrics_data['bucket_size_bytes'] = 'unavailable'

            # Get number of objects
            try:
                response = self.cloudwatch.get_metric_statistics(
                    Namespace='AWS/S3',
                    MetricName='NumberOfObjects',
                    Dimensions=[
                        {'Name': 'BucketName', 'Value': input_data.bucket_name},
                        {'Name': 'StorageType', 'Value': 'AllStorageTypes'}
                    ],
                    StartTime=start_time,
                    EndTime=end_time,
                    Period=86400,
                    Statistics=['Average']
                )
                if response['Datapoints']:
                    latest = max(response['Datapoints'], key=lambda x: x['Timestamp'])
                    metrics_data['number_of_objects'] = int(latest['Average'])
            except ClientError:
                metrics_data['number_of_objects'] = 'unavailable'

            return ToolOutput(
                success=True,
                message=f"Retrieved metrics for S3 bucket '{input_data.bucket_name}'",
                data=metrics_data
            )

        except ClientError as e:
            return self.handle_error(e, "get_s3_metrics")
        except Exception as e:
            return self.handle_error(e, "get_s3_metrics")


class GetLambdaMetricsInput(ToolInput):
    """Input for getting Lambda function metrics."""
    function_name: str = Field(..., description="Name of the Lambda function")
    days: int = Field(default=7, description="Number of days to retrieve metrics for")


class GetLambdaMetricsTool(BaseMCPTool):
    """Tool to get Lambda function metrics from CloudWatch."""

    def __init__(self):
        super().__init__(
            name="get_lambda_metrics",
            description="Get CloudWatch metrics for a Lambda function"
        )
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return GetLambdaMetricsInput

    async def execute(self, input_data: GetLambdaMetricsInput) -> ToolOutput:
        """Execute Lambda metrics retrieval.
        
        Args:
            input_data: Metrics parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("get_lambda_metrics", function_name=input_data.function_name)

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=input_data.days)

            metrics_data: Dict[str, Any] = {
                "function_name": input_data.function_name,
                "period_days": input_data.days
            }

            dimensions = [{'Name': 'FunctionName', 'Value': input_data.function_name}]

            # Get invocations
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Invocations',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            total_invocations = sum(dp['Sum'] for dp in response.get('Datapoints', []))
            metrics_data['total_invocations'] = int(total_invocations)

            # Get errors
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Errors',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            total_errors = sum(dp['Sum'] for dp in response.get('Datapoints', []))
            metrics_data['total_errors'] = int(total_errors)

            # Get duration
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/Lambda',
                MetricName='Duration',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Average', 'Maximum']
            )
            if response['Datapoints']:
                avg_duration = sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
                max_duration = max(dp['Maximum'] for dp in response['Datapoints'])
                metrics_data['average_duration_ms'] = round(avg_duration, 2)
                metrics_data['max_duration_ms'] = round(max_duration, 2)

            # Calculate error rate
            if total_invocations > 0:
                metrics_data['error_rate_percent'] = round((total_errors / total_invocations) * 100, 2)
            else:
                metrics_data['error_rate_percent'] = 0.0

            return ToolOutput(
                success=True,
                message=f"Retrieved metrics for Lambda function '{input_data.function_name}'",
                data=metrics_data
            )

        except ClientError as e:
            return self.handle_error(e, "get_lambda_metrics")
        except Exception as e:
            return self.handle_error(e, "get_lambda_metrics")


class GetDynamoDBMetricsInput(ToolInput):
    """Input for getting DynamoDB table metrics."""
    table_name: str = Field(..., description="Name of the DynamoDB table")
    days: int = Field(default=7, description="Number of days to retrieve metrics for")


class GetDynamoDBMetricsTool(BaseMCPTool):
    """Tool to get DynamoDB table metrics from CloudWatch."""

    def __init__(self):
        super().__init__(
            name="get_dynamodb_metrics",
            description="Get CloudWatch metrics for a DynamoDB table"
        )
        self.cloudwatch = boto3.client('cloudwatch', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return GetDynamoDBMetricsInput

    async def execute(self, input_data: GetDynamoDBMetricsInput) -> ToolOutput:
        """Execute DynamoDB metrics retrieval.
        
        Args:
            input_data: Metrics parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("get_dynamodb_metrics", table_name=input_data.table_name)

            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=input_data.days)

            metrics_data: Dict[str, Any] = {
                "table_name": input_data.table_name,
                "period_days": input_data.days
            }

            dimensions = [{'Name': 'TableName', 'Value': input_data.table_name}]

            # Get consumed read capacity
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/DynamoDB',
                MetricName='ConsumedReadCapacityUnits',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum', 'Average']
            )
            if response['Datapoints']:
                total_read = sum(dp['Sum'] for dp in response['Datapoints'])
                avg_read = sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
                metrics_data['total_read_capacity_units'] = round(total_read, 2)
                metrics_data['average_read_capacity_units'] = round(avg_read, 2)

            # Get consumed write capacity
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/DynamoDB',
                MetricName='ConsumedWriteCapacityUnits',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum', 'Average']
            )
            if response['Datapoints']:
                total_write = sum(dp['Sum'] for dp in response['Datapoints'])
                avg_write = sum(dp['Average'] for dp in response['Datapoints']) / len(response['Datapoints'])
                metrics_data['total_write_capacity_units'] = round(total_write, 2)
                metrics_data['average_write_capacity_units'] = round(avg_write, 2)

            # Get user errors
            response = self.cloudwatch.get_metric_statistics(
                Namespace='AWS/DynamoDB',
                MetricName='UserErrors',
                Dimensions=dimensions,
                StartTime=start_time,
                EndTime=end_time,
                Period=86400,
                Statistics=['Sum']
            )
            total_errors = sum(dp['Sum'] for dp in response.get('Datapoints', []))
            metrics_data['total_user_errors'] = int(total_errors)

            return ToolOutput(
                success=True,
                message=f"Retrieved metrics for DynamoDB table '{input_data.table_name}'",
                data=metrics_data
            )

        except ClientError as e:
            return self.handle_error(e, "get_dynamodb_metrics")
        except Exception as e:
            return self.handle_error(e, "get_dynamodb_metrics")
