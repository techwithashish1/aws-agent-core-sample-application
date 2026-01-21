"""Langchain integration for Bedrock."""

from typing import Any, List, Optional
from langchain_aws import ChatBedrock
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from config import settings


def create_bedrock_llm(
    model_id: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None
) -> ChatBedrock:
    """Create a Langchain ChatBedrock instance with tool calling support.
    
    Args:
        model_id: Bedrock model ID
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        
    Returns:
        ChatBedrock instance
    """
    return ChatBedrock(
        model_id=model_id or settings.bedrock_model_id,
        region_name=settings.bedrock_region,
        model_kwargs={
            "temperature": temperature or settings.temperature,
            "max_tokens": max_tokens or settings.max_tokens,
        }
    )


def create_agent_prompt() -> ChatPromptTemplate:
    """Create the prompt template for the AWS resource management agent.
    
    Returns:
        Chat prompt template
    """
    system_message = """You are an AI assistant specialized in managing AWS resources. 
You can help users create, configure, manage, and monitor AWS resources including S3 buckets, 
Lambda functions, and DynamoDB tables.

Key capabilities:
- Create and configure S3 buckets (bucket-level operations only, no object operations)
- Create, update, and manage Lambda functions
- Create, configure, and manage DynamoDB tables (no scan or query operations)
- Retrieve metrics and insights about AWS resources

Important limitations:
- You cannot perform data-level operations (S3 objects, DynamoDB items)
- You cannot execute DynamoDB scan or query operations
- You focus on infrastructure and configuration management only

When users request actions, you should:
1. Understand their requirements clearly
2. Select the appropriate tools to accomplish the task
3. Execute the operations step by step
4. **ALWAYS present the complete data returned by tools in your response**
5. When listing resources (buckets, functions, tables), present them in a clear, formatted list or table
6. Never give generic responses without showing actual data
7. Offer insights and recommendations when relevant

**CRITICAL INSTRUCTION FOR LISTING OPERATIONS:**
When you receive tool results containing lists of resources:
- Parse the data from the tool result
- Format it clearly with bullet points or as a table
- Include all relevant fields (names, dates, configurations, etc.)
- Example: If listing buckets, show:
  • bucket-name-1 (Created: 2024-01-15)
  • bucket-name-2 (Created: 2024-01-20)

Never respond with "I've listed the resources" - ALWAYS show the actual resources!

Always prioritize security best practices and ask for confirmation before destructive operations.
"""

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_message),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    return prompt
