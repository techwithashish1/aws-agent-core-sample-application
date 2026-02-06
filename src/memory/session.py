"""AgentCore Memory Session Handler for short-term memory.

This module provides session management for storing and retrieving
conversation events using AgentCore Memory.
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
import uuid

from bedrock_agentcore.memory import MemoryClient
from botocore.exceptions import ClientError

from config import settings

logger = logging.getLogger("agentcore-memory")


class MemorySession:
    """Manages a memory session for storing/retrieving conversation events.
    
    This class handles short-term memory operations:
    - Creating events from user-assistant exchanges
    - Listing past events for context retrieval
    - Managing session and actor identifiers
    """

    def __init__(
        self,
        memory_id: str,
        actor_id: Optional[str] = None,
        session_id: Optional[str] = None,
        region_name: Optional[str] = None
    ):
        """Initialize a memory session.
        
        Args:
            memory_id: The AgentCore Memory ID to use.
            actor_id: Unique identifier for the user/actor. Auto-generated if not provided.
            session_id: Unique identifier for the session. Auto-generated if not provided.
            region_name: AWS region. Defaults to settings.memory_region or settings.aws_region.
        """
        self.memory_id = memory_id
        self.region = region_name or settings.memory_region or settings.aws_region
        self.client = MemoryClient(region_name=self.region)
        
        # Generate unique IDs if not provided
        self.actor_id = actor_id or f"user_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        self.session_id = session_id or f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        
        logger.info(
            f"MemorySession initialized - memory_id: {self.memory_id}, "
            f"actor_id: {self.actor_id}, session_id: {self.session_id}"
        )

    def create_event(
        self,
        user_message: str,
        assistant_message: str
    ) -> Optional[Dict[str, Any]]:
        """Store a conversation event (user message + assistant response).
        
        Args:
            user_message: The user's input message.
            assistant_message: The assistant's response.
            
        Returns:
            Created event details or None if failed.
        """
        if not user_message.strip() or not assistant_message.strip():
            logger.warning("Skipping event creation - empty message detected")
            return None
        
        try:
            # Format messages as tuples of (content, role)
            messages: List[Tuple[str, str]] = [
                (user_message, "USER"),
                (assistant_message, "ASSISTANT")
            ]
            
            event = self.client.create_event(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                messages=messages
            )
            
            logger.info(f"Event created successfully for session {self.session_id}")
            return event
            
        except ClientError as e:
            logger.error(f"Failed to create event: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error creating event: {e}")
            return None

    def list_events(
        self,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """List recent events from the current session.
        
        Args:
            max_results: Maximum number of events to retrieve (default: 10).
            
        Returns:
            List of event dictionaries.
        """
        try:
            events = self.client.list_events(
                memory_id=self.memory_id,
                actor_id=self.actor_id,
                session_id=self.session_id,
                max_results=max_results
            )
            
            logger.info(f"Retrieved {len(events) if events else 0} events from session")
            return events if events else []
            
        except ClientError as e:
            logger.error(f"Failed to list events: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error listing events: {e}")
            return []

    def get_conversation_history(self, max_events: int = 5) -> str:
        """Get formatted conversation history for context.
        
        Args:
            max_events: Maximum number of past events to include.
            
        Returns:
            Formatted string of conversation history.
        """
        events = self.list_events(max_results=max_events)
        
        if not events:
            return "No previous conversation history."
        
        history_parts = []
        for event in events:
            # Events from list_events have 'payload' with 'conversational' messages
            # Structure: payload: [{conversational: {content: {text: "..."}, role: "USER"}}, ...]
            payload = event.get("payload", [])
            for item in payload:
                conversational = item.get("conversational", {})
                if conversational:
                    content_obj = conversational.get("content", {})
                    content = content_obj.get("text", "") if isinstance(content_obj, dict) else str(content_obj)
                    role = conversational.get("role", "UNKNOWN")
                    if role == "USER":
                        history_parts.append(f"User: {content}")
                    elif role == "ASSISTANT":
                        history_parts.append(f"Assistant: {content}")
        
        return "\n".join(history_parts) if history_parts else "No conversation history available."

    def new_session(self) -> str:
        """Start a new session while keeping the same actor.
        
        Returns:
            New session ID.
        """
        self.session_id = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        logger.info(f"New session started: {self.session_id}")
        return self.session_id


def create_memory_session(
    memory_id: Optional[str] = None,
    actor_id: Optional[str] = None,
    session_id: Optional[str] = None,
    region_name: Optional[str] = None
) -> Optional[MemorySession]:
    """Factory function to create a MemorySession.
    
    Args:
        memory_id: Memory ID. Falls back to settings.memory_id.
        actor_id: Actor ID. Auto-generated if not provided.
        session_id: Session ID. Auto-generated if not provided.
        region_name: AWS region.
        
    Returns:
        MemorySession instance or None if memory is disabled/unconfigured.
    """
    if not settings.memory_enabled:
        logger.info("Memory is disabled in settings")
        return None
    
    mem_id = memory_id or settings.memory_id
    
    if not mem_id:
        logger.warning("No memory_id configured. Set MEMORY_ID environment variable or settings.memory_id")
        return None
    
    return MemorySession(
        memory_id=mem_id,
        actor_id=actor_id,
        session_id=session_id,
        region_name=region_name
    )
