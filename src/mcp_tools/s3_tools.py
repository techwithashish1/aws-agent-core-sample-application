"""S3 MCP Tools for bucket-level operations."""

from typing import Dict, Any, Optional, List
from pydantic import Field
import boto3
from botocore.exceptions import ClientError

from .base_tool import BaseMCPTool, ToolInput, ToolOutput
from config import settings


class CreateS3BucketInput(ToolInput):
    """Input for creating an S3 bucket."""
    bucket_name: str = Field(..., description="Name of the S3 bucket to create")
    region: Optional[str] = Field(default=None, description="AWS region for the bucket")
    versioning_enabled: bool = Field(default=False, description="Enable versioning")
    encryption_enabled: bool = Field(default=True, description="Enable encryption")
    public_access_block: bool = Field(default=True, description="Block public access")
    tags: Optional[Dict[str, str]] = Field(default=None, description="Tags for the bucket")


class CreateS3BucketTool(BaseMCPTool):
    """Tool to create S3 buckets with configuration."""

    def __init__(self):
        super().__init__(
            name="create_s3_bucket",
            description="Create an S3 bucket with specified configuration"
        )
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return CreateS3BucketInput

    async def execute(self, input_data: CreateS3BucketInput) -> ToolOutput:
        """Execute S3 bucket creation.
        
        Args:
            input_data: Bucket creation parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("create_bucket", bucket_name=input_data.bucket_name)

            region = input_data.region or settings.aws_region

            # Create bucket
            if region == 'us-east-1':
                self.s3_client.create_bucket(Bucket=input_data.bucket_name)
            else:
                self.s3_client.create_bucket(
                    Bucket=input_data.bucket_name,
                    CreateBucketConfiguration={'LocationConstraint': region}
                )

            # Enable versioning if requested
            if input_data.versioning_enabled:
                self.s3_client.put_bucket_versioning(
                    Bucket=input_data.bucket_name,
                    VersioningConfiguration={'Status': 'Enabled'}
                )

            # Enable encryption if requested
            if input_data.encryption_enabled:
                self.s3_client.put_bucket_encryption(
                    Bucket=input_data.bucket_name,
                    ServerSideEncryptionConfiguration={
                        'Rules': [{
                            'ApplyServerSideEncryptionByDefault': {
                                'SSEAlgorithm': 'AES256'
                            }
                        }]
                    }
                )

            # Block public access if requested
            if input_data.public_access_block:
                self.s3_client.put_public_access_block(
                    Bucket=input_data.bucket_name,
                    PublicAccessBlockConfiguration={
                        'BlockPublicAcls': True,
                        'IgnorePublicAcls': True,
                        'BlockPublicPolicy': True,
                        'RestrictPublicBuckets': True
                    }
                )

            # Add tags if provided
            if input_data.tags:
                self.s3_client.put_bucket_tagging(
                    Bucket=input_data.bucket_name,
                    Tagging={
                        'TagSet': [
                            {'Key': k, 'Value': v} for k, v in input_data.tags.items()
                        ]
                    }
                )

            return ToolOutput(
                success=True,
                message=f"S3 bucket '{input_data.bucket_name}' created successfully",
                data={
                    "bucket_name": input_data.bucket_name,
                    "region": region,
                    "versioning": input_data.versioning_enabled,
                    "encryption": input_data.encryption_enabled
                }
            )

        except ClientError as e:
            return self.handle_error(e, "create_s3_bucket")
        except Exception as e:
            return self.handle_error(e, "create_s3_bucket")


class ListS3BucketsInput(ToolInput):
    """Input for listing S3 buckets."""
    prefix: Optional[str] = Field(default=None, description="Filter buckets by prefix")
    region: Optional[str] = Field(
        default=None, 
        description=(
            "Filter buckets by AWS region. Supports exact region codes (e.g., 'ap-southeast-1', 'us-east-1') "
            "or partial matches like 'asia', 'pacific', 'europe', etc. "
            "For Asia Pacific regions, use 'asia pacific', 'ap', or specific codes like 'ap-southeast-1'. "
            "IMPORTANT: Always specify this parameter when user requests buckets in a specific region."
        )
    )
    versioning_enabled: Optional[bool] = Field(
        default=None,
        description="Filter buckets by versioning status. True = only versioning-enabled buckets, False = only non-versioned buckets. Use when user asks about versioning."
    )
    encryption_enabled: Optional[bool] = Field(
        default=None,
        description="Filter buckets by encryption status. True = only encrypted buckets, False = only non-encrypted buckets. Use when user asks about encryption."
    )
    public_access_blocked: Optional[bool] = Field(
        default=None,
        description="Filter buckets by public access block status. True = only buckets with public access blocked, False = only public buckets. Use when user asks about public access."
    )
    name_pattern: Optional[str] = Field(
        default=None,
        description="Filter buckets by name pattern (case-insensitive substring match). Example: 'prod', 'backup', 'logs'. Use when user asks for buckets with specific names."
    )
    created_after: Optional[str] = Field(
        default=None,
        description="Filter buckets created after this date (ISO format: YYYY-MM-DD). Example: '2025-01-01'. Use when user asks about recent buckets."
    )
    created_before: Optional[str] = Field(
        default=None,
        description="Filter buckets created before this date (ISO format: YYYY-MM-DD). Example: '2026-01-01'. Use when user asks about old buckets."
    )
    tags: Optional[Dict[str, str]] = Field(
        default=None,
        description="Filter buckets by tags. Example: {'Environment': 'Production', 'Team': 'DataScience'}. Use when user asks for tagged buckets."
    )


class ListS3BucketsTool(BaseMCPTool):
    """Tool to list S3 buckets."""

    def __init__(self):
        super().__init__(
            name="list_s3_buckets",
            description=(
                "List S3 buckets with comprehensive filtering. "
                "ALWAYS use appropriate filters when user requests specific criteria: "
                "region (e.g., 'asia pacific'), versioning_enabled (True/False), encryption_enabled (True/False), "
                "public_access_blocked (True/False), name_pattern (substring match), created_after/before (YYYY-MM-DD), "
                "tags (dict). Multiple filters can be combined."
            )
        )
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return ListS3BucketsInput

    async def execute(self, input_data: ListS3BucketsInput) -> ToolOutput:
        """Execute S3 bucket listing with comprehensive filtering.
        
        Args:
            input_data: Listing parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("list_buckets")

            response = self.s3_client.list_buckets()
            buckets = response.get('Buckets', [])

            # Filter by prefix if provided
            if input_data.prefix:
                buckets = [b for b in buckets if b['Name'].startswith(input_data.prefix)]

            # Filter by name pattern if provided
            if input_data.name_pattern:
                buckets = [b for b in buckets if input_data.name_pattern.lower() in b['Name'].lower()]

            # Apply date filters early
            if input_data.created_after or input_data.created_before:
                from datetime import datetime
                filtered_by_date = []
                for bucket in buckets:
                    bucket_date = bucket['CreationDate'].replace(tzinfo=None)
                    if input_data.created_after:
                        try:
                            after_date = datetime.fromisoformat(input_data.created_after)
                            if bucket_date < after_date:
                                continue
                        except ValueError:
                            pass
                    if input_data.created_before:
                        try:
                            before_date = datetime.fromisoformat(input_data.created_before)
                            if bucket_date > before_date:
                                continue
                        except ValueError:
                            pass
                    filtered_by_date.append(bucket)
                buckets = filtered_by_date

            # Process remaining filters
            filtered_buckets = []
            for bucket in buckets:
                bucket_name = bucket['Name']
                bucket_info = {
                    "name": bucket_name,
                    "creation_date": bucket['CreationDate'].isoformat()
                }
                
                try:
                    # Get bucket location
                    location_response = self.s3_client.get_bucket_location(Bucket=bucket_name)
                    bucket_region = location_response.get('LocationConstraint') or 'us-east-1'
                    bucket_info['region'] = bucket_region
                    
                    # Apply region filter
                    if input_data.region and not self._matches_region(bucket_region, input_data.region):
                        continue
                    
                    # Apply versioning filter
                    if input_data.versioning_enabled is not None:
                        try:
                            versioning = self.s3_client.get_bucket_versioning(Bucket=bucket_name)
                            is_versioned = versioning.get('Status') == 'Enabled'
                            bucket_info['versioning'] = 'Enabled' if is_versioned else 'Disabled'
                            if is_versioned != input_data.versioning_enabled:
                                continue
                        except Exception:
                            continue
                    
                    # Apply encryption filter
                    if input_data.encryption_enabled is not None:
                        try:
                            self.s3_client.get_bucket_encryption(Bucket=bucket_name)
                            is_encrypted = True
                            bucket_info['encryption'] = 'Enabled'
                        except self.s3_client.exceptions.ServerSideEncryptionConfigurationNotFoundError:
                            is_encrypted = False
                            bucket_info['encryption'] = 'Disabled'
                        except Exception:
                            continue
                        if is_encrypted != input_data.encryption_enabled:
                            continue
                    
                    # Apply public access filter
                    if input_data.public_access_blocked is not None:
                        try:
                            public_block = self.s3_client.get_public_access_block(Bucket=bucket_name)
                            config = public_block['PublicAccessBlockConfiguration']
                            is_blocked = all([
                                config.get('BlockPublicAcls', False),
                                config.get('IgnorePublicAcls', False),
                                config.get('BlockPublicPolicy', False),
                                config.get('RestrictPublicBuckets', False)
                            ])
                            bucket_info['public_access'] = 'Blocked' if is_blocked else 'Allowed'
                        except self.s3_client.exceptions.NoSuchPublicAccessBlockConfiguration:
                            is_blocked = False
                            bucket_info['public_access'] = 'Allowed'
                        except Exception:
                            continue
                        if is_blocked != input_data.public_access_blocked:
                            continue
                    
                    # Apply tags filter
                    if input_data.tags:
                        try:
                            tag_response = self.s3_client.get_bucket_tagging(Bucket=bucket_name)
                            bucket_tags = {tag['Key']: tag['Value'] for tag in tag_response.get('TagSet', [])}
                            if not all(bucket_tags.get(k) == v for k, v in input_data.tags.items()):
                                continue
                            bucket_info['tags'] = bucket_tags
                        except self.s3_client.exceptions.NoSuchTagSet:
                            continue
                        except Exception:
                            continue
                    
                    filtered_buckets.append(bucket_info)
                    
                except Exception as e:
                    self.logger.warning(f"Could not process bucket {bucket_name}: {str(e)}")
                    continue

            # Build message
            filters_applied = []
            if input_data.region:
                filters_applied.append(f"region: {input_data.region}")
            if input_data.versioning_enabled is not None:
                filters_applied.append(f"versioning: {'enabled' if input_data.versioning_enabled else 'disabled'}")
            if input_data.encryption_enabled is not None:
                filters_applied.append(f"encryption: {'enabled' if input_data.encryption_enabled else 'disabled'}")
            if input_data.public_access_blocked is not None:
                filters_applied.append(f"public access: {'blocked' if input_data.public_access_blocked else 'allowed'}")
            if input_data.name_pattern:
                filters_applied.append(f"name pattern: '{input_data.name_pattern}'")
            if input_data.prefix:
                filters_applied.append(f"prefix: '{input_data.prefix}'")
            if input_data.created_after:
                filters_applied.append(f"created after: {input_data.created_after}")
            if input_data.created_before:
                filters_applied.append(f"created before: {input_data.created_before}")
            if input_data.tags:
                filters_applied.append(f"tags: {input_data.tags}")

            message = f"Found {len(filtered_buckets)} S3 bucket(s)"
            if filters_applied:
                message += f" (Filters: {', '.join(filters_applied)})"

            return ToolOutput(
                success=True,
                message=message,
                data={"buckets": filtered_buckets, "count": len(filtered_buckets)}
            )

        except ClientError as e:
            return self.handle_error(e, "list_s3_buckets")
        except Exception as e:
            return self.handle_error(e, "list_s3_buckets")

    def _matches_region(self, bucket_region: str, requested_region: str) -> bool:
        """Check if bucket region matches the requested region pattern."""
        bucket_region_lower = bucket_region.lower()
        requested_lower = requested_region.lower().strip()
        
        # Exact match
        if bucket_region_lower == requested_lower:
            return True
        
        # Handle region groups
        if requested_lower in ['asia pacific', 'asia', 'pacific', 'apac']:
            return bucket_region_lower.startswith('ap-')
        if requested_lower in ['europe', 'eu']:
            return bucket_region_lower.startswith('eu-')
        if requested_lower == 'us':
            return bucket_region_lower.startswith('us-')
        
        # Prefix match
        if bucket_region_lower.startswith(requested_lower):
            return True
        
        return False


class DeleteS3BucketInput(ToolInput):
    """Input for deleting an S3 bucket."""
    bucket_name: str = Field(..., description="Name of the S3 bucket to delete")
    force: bool = Field(default=False, description="Force delete even if not empty")


class DeleteS3BucketTool(BaseMCPTool):
    """Tool to delete S3 buckets."""

    def __init__(self):
        super().__init__(
            name="delete_s3_bucket",
            description="Delete an S3 bucket (bucket must be empty)"
        )
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return DeleteS3BucketInput

    async def execute(self, input_data: DeleteS3BucketInput) -> ToolOutput:
        """Execute S3 bucket deletion.
        
        Args:
            input_data: Deletion parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("delete_bucket", bucket_name=input_data.bucket_name)

            # Note: This only deletes empty buckets as per requirements
            # We don't delete objects (data-level operation)
            self.s3_client.delete_bucket(Bucket=input_data.bucket_name)

            return ToolOutput(
                success=True,
                message=f"S3 bucket '{input_data.bucket_name}' deleted successfully",
                data={"bucket_name": input_data.bucket_name}
            )

        except ClientError as e:
            if e.response['Error']['Code'] == 'BucketNotEmpty':
                return ToolOutput(
                    success=False,
                    message=f"Bucket '{input_data.bucket_name}' is not empty",
                    error="Cannot delete non-empty bucket (object operations not allowed)"
                )
            return self.handle_error(e, "delete_s3_bucket")
        except Exception as e:
            return self.handle_error(e, "delete_s3_bucket")


class GetS3BucketInfoInput(ToolInput):
    """Input for getting S3 bucket information."""
    bucket_name: str = Field(..., description="Name of the S3 bucket")


class GetS3BucketInfoTool(BaseMCPTool):
    """Tool to get S3 bucket information and configuration."""

    def __init__(self):
        super().__init__(
            name="get_s3_bucket_info",
            description="Get detailed information about an S3 bucket"
        )
        self.s3_client = boto3.client('s3', region_name=settings.aws_region)

    @property
    def input_model(self) -> type[ToolInput]:
        return GetS3BucketInfoInput

    async def execute(self, input_data: GetS3BucketInfoInput) -> ToolOutput:
        """Execute S3 bucket info retrieval.
        
        Args:
            input_data: Info retrieval parameters
            
        Returns:
            Tool execution result
        """
        try:
            self.log_execution("get_bucket_info", bucket_name=input_data.bucket_name)

            info: Dict[str, Any] = {"bucket_name": input_data.bucket_name}

            # Get bucket location
            try:
                location = self.s3_client.get_bucket_location(Bucket=input_data.bucket_name)
                info['region'] = location['LocationConstraint'] or 'us-east-1'
            except ClientError:
                info['region'] = 'unknown'

            # Get versioning status
            try:
                versioning = self.s3_client.get_bucket_versioning(Bucket=input_data.bucket_name)
                info['versioning'] = versioning.get('Status', 'Disabled')
            except ClientError:
                info['versioning'] = 'unknown'

            # Get encryption status
            try:
                encryption = self.s3_client.get_bucket_encryption(Bucket=input_data.bucket_name)
                info['encryption'] = 'Enabled'
            except ClientError as e:
                if e.response['Error']['Code'] == 'ServerSideEncryptionConfigurationNotFoundError':
                    info['encryption'] = 'Disabled'
                else:
                    info['encryption'] = 'unknown'

            # Get tags
            try:
                tags = self.s3_client.get_bucket_tagging(Bucket=input_data.bucket_name)
                info['tags'] = {tag['Key']: tag['Value'] for tag in tags.get('TagSet', [])}
            except ClientError:
                info['tags'] = {}

            return ToolOutput(
                success=True,
                message=f"Retrieved information for bucket '{input_data.bucket_name}'",
                data=info
            )

        except ClientError as e:
            return self.handle_error(e, "get_s3_bucket_info")
        except Exception as e:
            return self.handle_error(e, "get_s3_bucket_info")
