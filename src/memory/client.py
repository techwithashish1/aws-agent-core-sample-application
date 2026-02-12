"""AgentCore Memory Client for AWS Resource Manager.

This module provides memory management capabilities using Amazon Bedrock AgentCore Memory.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger("agentcore-memory")


class MemoryManager:
    """Manager for AgentCore Memory operations.
    
    Provides methods to create, manage, and interact with AgentCore Memory
    for maintaining conversation context and user preferences.
    """

    def __init__(self, region_name: Optional[str] = None):
        """Initialize the Memory Manager.
        
        Args:
            region_name: AWS region for the memory client. Defaults to settings.aws_region.
        """
        self.region = region_name or settings.aws_region
        self.client = MemoryClient(region_name=self.region)
        self.memory_id: Optional[str] = None
        # Memory names must match: [a-zA-Z][a-zA-Z0-9_]{0,47} (no hyphens)
        self.memory_name: str = settings.agent_name.replace("-", "_") + "_memory"
        
        logger.info(f"MemoryManager initialized for region: {self.region}")

    def create_memory(
        self,
        name: Optional[str] = None,
        description: Optional[str] = None,
        strategies: Optional[List[Dict[str, Any]]] = None,
        event_expiry_days: int = 7,
        max_wait: int = 300,
        poll_interval: int = 10
    ) -> Dict[str, Any]:
        """Create a new AgentCore Memory resource.
        
        Args:
            name: Unique name for the memory. Defaults to agent_name-memory.
            description: Human-readable description of the memory.
            strategies: List of memory extraction strategies (SEMANTIC, SUMMARY, USER_PREFERENCES, CUSTOM).
                       Empty list for short-term memory only.
            event_expiry_days: Number of days before events expire.
            max_wait: Maximum time to wait for memory creation (seconds).
            poll_interval: Interval to check status (seconds).
            
        Returns:
            Dict containing memory details including 'id'.
            
        Raises:
            ClientError: If memory creation fails.
        """
        memory_name = name or self.memory_name
        memory_description = description or f"Memory for {settings.agent_description}"
        memory_strategies = strategies if strategies is not None else []
        
        try:
            logger.info(f"Creating memory: {memory_name}")
            
            memory = self.client.create_memory_and_wait(
                name=memory_name,
                description=memory_description,
                strategies=memory_strategies,
                event_expiry_days=event_expiry_days,
                max_wait=max_wait,
                poll_interval=poll_interval
            )
            
            self.memory_id = memory['id']
            logger.info(f"Memory created successfully with ID: {self.memory_id}")
            
            return memory
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ValidationException' and "already exists" in str(e):
                logger.info(f"Memory '{memory_name}' already exists. Retrieving existing memory...")
                return self.get_existing_memory(memory_name)
            else:
                logger.error(f"Failed to create memory: {e}")
                raise

    def get_existing_memory(self, memory_name: str) -> Dict[str, Any]:
        """Retrieve an existing memory by name.
        
        Args:
            memory_name: Name of the memory to find.
            
        Returns:
            Dict containing memory details.
            
        Raises:
            ValueError: If memory is not found.
        """
        memories = self.client.list_memories()
        
        for memory in memories:
            if memory['id'].startswith(memory_name) or memory.get('name') == memory_name:
                self.memory_id = memory['id']
                logger.info(f"Found existing memory ID: {self.memory_id}")
                return memory
        
        raise ValueError(f"Memory with name '{memory_name}' not found")

    def list_memories(self) -> List[Dict[str, Any]]:
        """List all available memories.
        
        Returns:
            List of memory dictionaries.
        """
        return self.client.list_memories()

    def delete_memory(
        self,
        memory_id: Optional[str] = None,
        max_wait: int = 300,
        poll_interval: int = 10
    ) -> None:
        """Delete a memory resource.
        
        Args:
            memory_id: ID of memory to delete. Defaults to current memory_id.
            max_wait: Maximum time to wait for deletion.
            poll_interval: Interval to check status.
        """
        target_id = memory_id or self.memory_id
        
        if not target_id:
            logger.warning("No memory ID specified for deletion")
            return
        
        logger.info(f"Deleting memory: {target_id}")
        self.client.delete_memory_and_wait(
            memory_id=target_id,
            max_wait=max_wait,
            poll_interval=poll_interval
        )
        
        if target_id == self.memory_id:
            self.memory_id = None
        
        logger.info(f"Memory {target_id} deleted successfully")

    def get_memory_info(self, memory_id: Optional[str] = None) -> Dict[str, Any]:
        """Get information about a specific memory.
        
        Args:
            memory_id: ID of the memory. Defaults to current memory_id.
            
        Returns:
            Dict containing memory information.
        """
        target_id = memory_id or self.memory_id
        
        if not target_id:
            raise ValueError("No memory ID specified")
        
        return self.client.get_memory(memory_id=target_id)


def get_memory_client(region_name: Optional[str] = None) -> MemoryClient:
    """Get a raw MemoryClient instance.
    
    Args:
        region_name: AWS region. Defaults to settings.aws_region.
        
    Returns:
        MemoryClient instance.
    """
    region = region_name or settings.aws_region
    return MemoryClient(region_name=region)
