"""Langgraph agent implementation for AWS resource management."""

import os
from typing import Dict, Any, List, Optional, TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import BaseTool, StructuredTool, tool
import operator
import structlog

from bedrock import BedrockClient
from bedrock.langchain_integration import create_bedrock_llm, create_agent_prompt
from mcp_tools import (
    CreateS3BucketTool,
    ListS3BucketsTool,
    DeleteS3BucketTool,
    GetS3BucketInfoTool,
    CreateLambdaFunctionTool,
    ListLambdaFunctionsTool,
    UpdateLambdaConfigTool,
    DeleteLambdaFunctionTool,
    GetLambdaFunctionInfoTool,
    CreateDynamoDBTableTool,
    ListDynamoDBTablesTool,
    DescribeDynamoDBTableTool,
    DeleteDynamoDBTableTool,
    UpdateDynamoDBTableTool,
)
from config import settings
from memory import create_memory_session, MemorySession

logger = structlog.get_logger()


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], operator.add]


def create_langchain_tools() -> List[BaseTool]:
    """Create Langchain-compatible tools from MCP tools.
    
    Returns:
        List of Langchain tools
    """
    tools = []
    
    def create_tool_wrapper(tool_instance):
        """Create a wrapper function for async tool execution."""
        async def wrapper(**kwargs):
            input_data = tool_instance.input_model(**kwargs)
            result = await tool_instance.execute(input_data)
            # Convert ToolOutput to string for LangChain
            return str(result)
        return wrapper

    # S3 Tools
    s3_create = CreateS3BucketTool()
    tools.append(StructuredTool.from_function(
        name=s3_create.name,
        description=s3_create.description,
        args_schema=s3_create.input_model,
        func=lambda **kwargs: str(s3_create.execute(s3_create.input_model(**kwargs))),
        coroutine=create_tool_wrapper(s3_create)
    ))

    s3_list = ListS3BucketsTool()
    tools.append(StructuredTool.from_function(
        name=s3_list.name,
        description=s3_list.description,
        args_schema=s3_list.input_model,
        func=lambda **kwargs: str(s3_list.execute(s3_list.input_model(**kwargs))),
        coroutine=create_tool_wrapper(s3_list)
    ))

    s3_delete = DeleteS3BucketTool()
    tools.append(StructuredTool.from_function(
        name=s3_delete.name,
        description=s3_delete.description,
        args_schema=s3_delete.input_model,
        func=lambda **kwargs: str(s3_delete.execute(s3_delete.input_model(**kwargs))),
        coroutine=create_tool_wrapper(s3_delete)
    ))

    s3_info = GetS3BucketInfoTool()
    tools.append(StructuredTool.from_function(
        name=s3_info.name,
        description=s3_info.description,
        args_schema=s3_info.input_model,
        func=lambda **kwargs: str(s3_info.execute(s3_info.input_model(**kwargs))),
        coroutine=create_tool_wrapper(s3_info)
    ))

    # Lambda Tools
    lambda_create = CreateLambdaFunctionTool()
    tools.append(StructuredTool.from_function(
        name=lambda_create.name,
        description=lambda_create.description,
        args_schema=lambda_create.input_model,
        func=lambda **kwargs: str(lambda_create.execute(lambda_create.input_model(**kwargs))),
        coroutine=create_tool_wrapper(lambda_create)
    ))

    lambda_list = ListLambdaFunctionsTool()
    tools.append(StructuredTool.from_function(
        name=lambda_list.name,
        description=lambda_list.description,
        args_schema=lambda_list.input_model,
        func=lambda **kwargs: str(lambda_list.execute(lambda_list.input_model(**kwargs))),
        coroutine=create_tool_wrapper(lambda_list)
    ))

    lambda_update = UpdateLambdaConfigTool()
    tools.append(StructuredTool.from_function(
        name=lambda_update.name,
        description=lambda_update.description,
        args_schema=lambda_update.input_model,
        func=lambda **kwargs: str(lambda_update.execute(lambda_update.input_model(**kwargs))),
        coroutine=create_tool_wrapper(lambda_update)
    ))

    lambda_delete = DeleteLambdaFunctionTool()
    tools.append(StructuredTool.from_function(
        name=lambda_delete.name,
        description=lambda_delete.description,
        args_schema=lambda_delete.input_model,
        func=lambda **kwargs: str(lambda_delete.execute(lambda_delete.input_model(**kwargs))),
        coroutine=create_tool_wrapper(lambda_delete)
    ))

    lambda_info = GetLambdaFunctionInfoTool()
    tools.append(StructuredTool.from_function(
        name=lambda_info.name,
        description=lambda_info.description,
        args_schema=lambda_info.input_model,
        func=lambda **kwargs: str(lambda_info.execute(lambda_info.input_model(**kwargs))),
        coroutine=create_tool_wrapper(lambda_info)
    ))

    # DynamoDB Tools
    ddb_create = CreateDynamoDBTableTool()
    tools.append(StructuredTool.from_function(
        name=ddb_create.name,
        description=ddb_create.description,
        args_schema=ddb_create.input_model,
        func=lambda **kwargs: str(ddb_create.execute(ddb_create.input_model(**kwargs))),
        coroutine=create_tool_wrapper(ddb_create)
    ))

    ddb_list = ListDynamoDBTablesTool()
    tools.append(StructuredTool.from_function(
        name=ddb_list.name,
        description=ddb_list.description,
        args_schema=ddb_list.input_model,
        func=lambda **kwargs: str(ddb_list.execute(ddb_list.input_model(**kwargs))),
        coroutine=create_tool_wrapper(ddb_list)
    ))

    ddb_describe = DescribeDynamoDBTableTool()
    tools.append(StructuredTool.from_function(
        name=ddb_describe.name,
        description=ddb_describe.description,
        args_schema=ddb_describe.input_model,
        func=lambda **kwargs: str(ddb_describe.execute(ddb_describe.input_model(**kwargs))),
        coroutine=create_tool_wrapper(ddb_describe)
    ))

    ddb_delete = DeleteDynamoDBTableTool()
    tools.append(StructuredTool.from_function(
        name=ddb_delete.name,
        description=ddb_delete.description,
        args_schema=ddb_delete.input_model,
        func=lambda **kwargs: str(ddb_delete.execute(ddb_delete.input_model(**kwargs))),
        coroutine=create_tool_wrapper(ddb_delete)
    ))

    ddb_update = UpdateDynamoDBTableTool()
    tools.append(StructuredTool.from_function(
        name=ddb_update.name,
        description=ddb_update.description,
        args_schema=ddb_update.input_model,
        func=lambda **kwargs: str(ddb_update.execute(ddb_update.input_model(**kwargs))),
        coroutine=create_tool_wrapper(ddb_update)
    ))

    return tools


def load_gateway_tools() -> List[BaseTool]:
    """Load tools from AgentCore Gateway.
    
    Returns:
        List of LangChain tools from gateway, or empty list if unavailable
    """
    try:
        from gateway_integration import MCPGatewayClient, create_gateway_tools
        
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "agentcore_gateway",
            "gateway_config.json"
        )
        
        if not os.path.exists(config_path):
            logger.warning("gateway_config_not_found", path=config_path)
            return []
        
        logger.info("loading_gateway_config", path=config_path)
        client = MCPGatewayClient.from_config(config_path)
        logger.info("gateway_client_created", 
                   gateway_url=client.gateway_url,
                   token_url=client.cognito_token_url)
        
        tools = create_gateway_tools(client)
        logger.info("gateway_tools_loaded", 
                   count=len(tools), 
                   tools=[t.name for t in tools])
        return tools
        
    except ImportError as e:
        logger.warning("gateway_integration_not_available", error=str(e))
        return []
    except Exception as e:
        import traceback
        logger.error("gateway_tools_load_failed", 
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc())
        return []


class AWSResourceAgent:
    """AWS Resource Management Agent using Langgraph."""

    def __init__(
        self,
        include_gateway_tools: bool = True,
        memory_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Initialize the agent.
        
        Args:
            include_gateway_tools: Whether to include tools from AgentCore Gateway
            memory_id: AgentCore Memory ID for short-term memory. Falls back to settings.memory_id.
            actor_id: Unique identifier for the user. Auto-generated if not provided.
            session_id: Unique identifier for the session. Auto-generated if not provided.
        """
        self.logger = logger.bind(component="aws_resource_agent")
        self.tools = create_langchain_tools()
        
        # Add gateway tools if enabled
        if include_gateway_tools:
            gateway_tools = load_gateway_tools()
            if gateway_tools:
                self.tools.extend(gateway_tools)
                self.logger.info("gateway_tools_added", count=len(gateway_tools))
        
        # Initialize memory session for short-term memory
        self.memory_session: Optional[MemorySession] = None
        if settings.memory_enabled:
            self.memory_session = create_memory_session(
                memory_id=memory_id,
                actor_id=actor_id,
                session_id=session_id
            )
            if self.memory_session:
                # Add list_conversation_history tool
                self.tools.append(self._create_memory_tool())
                self.logger.info(
                    "memory_enabled",
                    memory_id=self.memory_session.memory_id,
                    session_id=self.memory_session.session_id
                )
        
        self.llm = create_bedrock_llm()
        
        # Bind tools to LLM for function calling
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        self.tool_node = ToolNode(self.tools)
        self.graph = self._create_graph()
        
        self.logger.info(
            "agent_initialized",
            num_tools=len(self.tools),
            model=settings.bedrock_model_id,
            memory_enabled=self.memory_session is not None
        )

    def _create_memory_tool(self) -> BaseTool:
        """Create a tool for retrieving conversation history.
        
        Returns:
            LangChain tool for listing past events
        """
        memory_session = self.memory_session
        
        @tool
        def list_conversation_history(max_events: int = 5) -> str:
            """Retrieve recent conversation history from memory.
            
            Use this tool when you need to recall what was discussed earlier
            in the conversation, or to understand context from previous interactions.
            
            Args:
                max_events: Maximum number of past events to retrieve (default: 5)
                
            Returns:
                Formatted conversation history
            """
            if not memory_session:
                return "Memory is not available."
            return memory_session.get_conversation_history(max_events=max_events)
        
        return list_conversation_history

    def _create_graph(self) -> StateGraph:
        """Create the Langgraph state graph.
        
        Returns:
            State graph
        """
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("agent", self._run_agent)
        workflow.add_node("action", self.tool_node)

        # Set entry point
        workflow.set_entry_point("agent")

        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "action",
                "end": END,
            }
        )

        # Add edge from action to agent
        workflow.add_edge("action", "agent")

        return workflow.compile()

    async def _run_agent(self, state: AgentState) -> Dict[str, Any]:
        """Run the agent reasoning step.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        messages = state["messages"]
        
        self.logger.info("agent_reasoning", message_count=len(messages))
        
        # Build system message with memory awareness
        system_content = """You are an AI assistant specialized in managing AWS resources.
You can help users create, configure, manage, and monitor AWS resources including S3 buckets,
Lambda functions, and DynamoDB tables.

MEMORY CAPABILITIES:
- You have access to conversation history using the list_conversation_history tool
- ALWAYS use this tool first when a user asks about previous conversations, their name, 
  projects they mentioned, or any contextual information from earlier interactions
- If a user asks "what is my name" or "what did we discuss", USE the list_conversation_history tool

Key capabilities:
- Create and configure S3 buckets
- Create, update, and manage Lambda functions  
- Create, configure, and manage DynamoDB tables

When listing resources, ALWAYS show the actual data returned by tools.
Always prioritize security best practices."""

        # Prepend system message if not already present
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=system_content)] + list(messages)
        
        # Invoke LLM with tools to get decision
        response = await self.llm_with_tools.ainvoke(messages)
        
        self.logger.info(
            "llm_response",
            has_tool_calls=bool(response.tool_calls) if hasattr(response, 'tool_calls') else False,
            content_preview=response.content[:100] if response.content else None
        )
        
        return {"messages": [response]}

    async def _execute_tool(self, state: AgentState) -> Dict[str, Any]:
        """Execute a tool based on agent decision.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        last_message = state["messages"][-1]
        
        # Extract tool calls from the last message
        tool_calls = last_message.tool_calls if hasattr(last_message, 'tool_calls') else []
        
        if not tool_calls:
            self.logger.warning("no_tool_calls_found")
            return {"messages": []}
        
        # Execute each tool call
        tool_messages = []
        for tool_call in tool_calls:
            tool_name = tool_call["name"]
            tool_input = tool_call["args"]
            
            self.logger.info("executing_tool", tool=tool_name, input=tool_input)
            
            try:
                # Execute tool
                result = await self.tool_executor.ainvoke(tool_call)
                
                self.logger.info("tool_executed", tool=tool_name, success=True)
                
                # Create tool message with result
                tool_message = ToolMessage(
                    content=str(result),
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
                self.logger.info("tool_result_content", tool=tool_name, content=str(result)[:500])
                tool_messages.append(tool_message)
                
            except Exception as e:
                self.logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                
                # Create error message
                tool_message = ToolMessage(
                    content=f"Error executing {tool_name}: {str(e)}",
                    tool_call_id=tool_call["id"],
                    name=tool_name
                )
                tool_messages.append(tool_message)
        
        return {"messages": tool_messages}

    def _should_continue(self, state: AgentState) -> str:
        """Determine if agent should continue or end.
        
        Args:
            state: Current agent state
            
        Returns:
            Next node name ("continue" to execute tools, "end" to finish)
        """
        messages = state["messages"]
        last_message = messages[-1]
        
        # If last message has tool calls, continue to execute them
        if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
            return "continue"
        
        # Otherwise, we're done
        return "end"

    async def execute(self, user_input: str) -> str:
        """Execute a user command through the agent.
        
        Args:
            user_input: User's natural language command
            
        Returns:
            Agent's response
        """
        try:
            self.logger.info("executing_command", input=user_input)
            
            # Create initial state with user message
            initial_state = {
                "messages": [HumanMessage(content=user_input)]
            }
            
            # Run the Langgraph workflow
            result = await self.graph.ainvoke(initial_state)
            
            # Extract final response from the last message
            final_message = result["messages"][-1]
            
            if isinstance(final_message, AIMessage):
                response = final_message.content
            else:
                response = str(final_message.content) if hasattr(final_message, "content") else str(final_message)
            
            # Check if there are tool results in the message history
            # If the AI response is generic, append the tool data
            tool_results = []
            for msg in result["messages"]:
                if isinstance(msg, ToolMessage):
                    tool_results.append(msg.content)
            
            # If we have tool results and the response is short/generic, include the data
            if tool_results and len(response) < 300:
                response += "\n\n" + "\n\n".join(tool_results)
            
            self.logger.info("command_executed", response_length=len(response))
            
            # Store conversation event in memory (short-term memory)
            if self.memory_session and response.strip():
                try:
                    self.memory_session.create_event(
                        user_message=user_input,
                        assistant_message=response
                    )
                    self.logger.info("conversation_stored_in_memory")
                except Exception as mem_error:
                    self.logger.warning(
                        "memory_store_failed",
                        error=str(mem_error)
                    )
            
            return response
            
        except Exception as e:
            self.logger.error("execution_failed", error=str(e), error_type=type(e).__name__)
            return f"Error executing command: {str(e)}"

    def new_session(self) -> Optional[str]:
        """Start a new memory session while keeping the same actor.
        
        Returns:
            New session ID or None if memory is not enabled.
        """
        if self.memory_session:
            return self.memory_session.new_session()
        return None

    def set_session(self, session_id: str, actor_id: Optional[str] = None) -> None:
        """Set the memory session identifiers for the current invocation.
        
        This allows maintaining conversation context across multiple invocations
        by using consistent session_id and actor_id.
        
        Args:
            session_id: The session identifier (e.g., from AgentCore context).
            actor_id: Optional actor identifier. If not provided, keeps existing.
        """
        if self.memory_session:
            self.memory_session.session_id = session_id
            if actor_id:
                self.memory_session.actor_id = actor_id
            self.logger.info(
                "session_updated",
                session_id=session_id,
                actor_id=self.memory_session.actor_id
            )

    def get_session_info(self) -> Dict[str, Any]:
        """Get current memory session information.
        
        Returns:
            Dictionary with session details.
        """
        if self.memory_session:
            return {
                "memory_enabled": True,
                "memory_id": self.memory_session.memory_id,
                "actor_id": self.memory_session.actor_id,
                "session_id": self.memory_session.session_id,
                "region": self.memory_session.region
            }
        return {"memory_enabled": False}

    def execute_sync(self, user_input: str) -> str:
        """Synchronous wrapper for execute.
        
        Args:
            user_input: User's natural language command
            
        Returns:
            Agent's response
        """
        import asyncio
        return asyncio.run(self.execute(user_input))
