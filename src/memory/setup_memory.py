"""Script to create and setup AgentCore Memory for AWS Resource Manager.

This script creates a memory resource that can be used by the agent for:
- Short-term memory: Session-based conversation context
- Long-term memory: Persistent preferences and facts (when strategies are enabled)

Usage:
    python -m memory.setup_memory

"""

import argparse
import logging
import sys
from typing import List, Dict, Any

from bedrock_agentcore.memory.constants import StrategyType
from memory.client import MemoryManager
from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("agentcore-memory")


def sanitize_name(name: str) -> str:
    """Sanitize name to comply with AgentCore Memory naming constraints.
    
    Names must match pattern: [a-zA-Z][a-zA-Z0-9_]{0,47}
    """
    return name.replace("-", "_")


def create_short_term_memory(manager: MemoryManager) -> Dict[str, Any]:
    """Create a short-term memory (no extraction strategies).
    
    Short-term memory stores raw conversation events for session continuity.
    Events expire after the configured number of days.
    
    Args:
        manager: MemoryManager instance.
        
    Returns:
        Created memory details.
    """
    memory_name = sanitize_name(f"{settings.agent_name}_short_term")
    return manager.create_memory(
        name=memory_name,
        description=f"Short-term memory for {settings.agent_name} - session context",
        strategies=[],  # No strategies = short-term memory only
        event_expiry_days=settings.memory_event_expiry_days
    )


def create_long_term_memory(
    manager: MemoryManager,
    include_semantic: bool = True,
    include_summary: bool = True,
    include_user_preferences: bool = True
) -> Dict[str, Any]:
    """Create a long-term memory with extraction strategies.
    
    Long-term memory automatically extracts and stores:
    - SEMANTIC: Factual information with vector embeddings
    - SUMMARY: Conversation summaries
    - USER_PREFERENCES: User-specific preferences
    
    Args:
        manager: MemoryManager instance.
        include_semantic: Include semantic memory strategy.
        include_summary: Include summary memory strategy.
        include_user_preferences: Include user preferences strategy.
        
    Returns:
        Created memory details.
    """
    strategies: List[Dict[str, Any]] = []
    
    agent_name_safe = sanitize_name(settings.agent_name)
    
    if include_semantic:
        strategies.append({
            StrategyType.SEMANTIC.value: {
                "name": f"{agent_name_safe}_semantic",
                "description": "Stores factual information with vector embeddings",
                "namespaces": [f"{agent_name_safe}_facts"]
            }
        })
    
    if include_summary:
        strategies.append({
            StrategyType.SUMMARY.value: {
                "name": f"{agent_name_safe}_summary",
                "description": "Creates and maintains conversation summaries",
                "namespaces": [f"{agent_name_safe}_summaries/{{sessionId}}"]
            }
        })
    
    if include_user_preferences:
        strategies.append({
            StrategyType.USER_PREFERENCE.value: {
                "name": f"{agent_name_safe}_preferences",
                "description": "Tracks user-specific preferences and settings",
                "namespaces": [f"{agent_name_safe}_prefs"]
            }
        })
    
    memory_name = sanitize_name(f"{settings.agent_name}_long_term")
    return manager.create_memory(
        name=memory_name,
        description=f"Long-term memory for {settings.agent_name} - persistent context",
        strategies=strategies,
        event_expiry_days=30  # Longer expiry for long-term memory
    )


def list_all_memories(manager: MemoryManager) -> None:
    """List all existing memories."""
    memories = manager.list_memories()
    
    if not memories:
        print("\nNo memories found.")
        return
    
    print(f"\n{'='*60}")
    print("Existing Memories:")
    print(f"{'='*60}")
    
    for memory in memories:
        print(f"\nID: {memory.get('id', 'N/A')}")
        print(f"Name: {memory.get('name', 'N/A')}")
        print(f"Status: {memory.get('status', 'N/A')}")
        print(f"Description: {memory.get('description', 'N/A')}")
        print("-" * 40)


def main():
    """Main entry point for memory setup."""
    parser = argparse.ArgumentParser(
        description="Setup AgentCore Memory for AWS Resource Manager"
    )
    parser.add_argument(
        "--type",
        choices=["short-term", "long-term", "both"],
        default="short-term",
        help="Type of memory to create (default: short-term)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing memories"
    )
    parser.add_argument(
        "--delete",
        type=str,
        help="Delete a memory by ID"
    )
    parser.add_argument(
        "--region",
        type=str,
        default=None,
        help="AWS region (default: from settings)"
    )
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = MemoryManager(region_name=args.region)
    
    # Handle list command
    if args.list:
        list_all_memories(manager)
        return
    
    # Handle delete command
    if args.delete:
        try:
            manager.delete_memory(memory_id=args.delete)
            print(f"Memory {args.delete} deleted successfully")
        except Exception as e:
            print(f"Error deleting memory: {e}")
            sys.exit(1)
        return
    
    # Create memory based on type
    try:
        if args.type == "short-term":
            memory = create_short_term_memory(manager)
            print(f"\n✅ Short-term memory created successfully!")
            
        elif args.type == "long-term":
            memory = create_long_term_memory(manager)
            print(f"\n✅ Long-term memory created successfully!")
            
        elif args.type == "both":
            short_memory = create_short_term_memory(manager)
            print(f"\n✅ Short-term memory created: {short_memory['id']}")
            
            # Create new manager instance for second memory
            manager2 = MemoryManager(region_name=args.region)
            long_memory = create_long_term_memory(manager2)
            print(f"✅ Long-term memory created: {long_memory['id']}")
        
        # Show created memory details
        print(f"\n{'='*60}")
        print("Memory Details:")
        print(f"{'='*60}")
        print(f"ID: {manager.memory_id}")
        print(f"Region: {manager.region}")
        print(f"\nYou can now use this memory ID in your agent configuration.")
        
    except Exception as e:
        logger.error(f"Failed to create memory: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
