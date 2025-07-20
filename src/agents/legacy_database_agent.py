"""
Database Agent for MCP Toolbox Integration.

This module provides a sophisticated database agent that uses MCP Toolbox tools
to interact with databases through LangChain and can be integrated with LangGraph workflows.
"""

import logging
import asyncio
import os
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import json

from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..client.mcp_client import MCPProtocolClient, MCPToolboxClient
from ..client.langchain_tools import MCPLangChainTools, create_langchain_tools_sync
from ..utils.config import ConfigManager
from ..utils.llm_factory import create_llm_from_config


logger = logging.getLogger(__name__)


class DatabaseAgent:
    """
    An intelligent database agent that can understand natural language queries
    and execute appropriate database operations using MCP Toolbox tools.
    """
    
    def __init__(
        self,
        mcp_client: Union[MCPProtocolClient, MCPToolboxClient],
        llm: Optional[BaseLanguageModel] = None,
        toolset_name: Optional[str] = None,
        temperature: float = 0.1,
        max_iterations: int = 5,
        use_mcp_protocol: bool = True,
        hub_url: str = "http://localhost:5000/mcp",
        agent_port: int = 8002
    ):
        """
        Initialize the Database Agent.
        
        Args:
            mcp_client: MCP client instance (Protocol or Toolbox client)
            llm: Language model to use (defaults to Anthropic Claude Haiku)
            toolset_name: Specific toolset to load (if None, loads all tools)
            temperature: LLM temperature for response generation
            max_iterations: Maximum number of agent iterations
            use_mcp_protocol: Whether to use the new MCP protocol (True) or legacy client (False)
            hub_url: URL of the central MCP hub for registration and discovery
            agent_port: Port for this agent's MCP server
        """
        import uuid
        import json
        
        self.mcp_client = mcp_client
        self.toolset_name = toolset_name
        self.temperature = temperature
        self.max_iterations = max_iterations
        self.use_mcp_protocol = use_mcp_protocol and isinstance(mcp_client, MCPProtocolClient)
        self.hub_url = hub_url
        self.agent_port = agent_port
        self.agent_id = f"database-agent-{uuid.uuid4().hex[:8]}"
        
        # Hub integration
        self.registered_with_hub = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Store for later use
        self.uuid = uuid
        self.json = json
        
        # Initialize LLM based on configuration
        if llm is None:
            try:
                config_manager = ConfigManager()
                self.llm = create_llm_from_config(
                    config_manager=config_manager,
                    temperature=temperature
                )
            except Exception as e:
                logger.warning(f"Failed to load configuration, using default Anthropic Claude: {e}")
                # Fallback to direct initialization
                self.llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=temperature,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    streaming=True
                )
        else:
            self.llm = llm
        
        # Initialize tools factory
        self.tools_factory = MCPLangChainTools(mcp_client)
        
        # Load tools
        self.tools = self._load_tools()
        
        # Create agent
        self.agent_executor = self._create_agent()
        
        logger.info(f"Initialized Database Agent with {len(self.tools)} tools")
    
    def _load_tools(self) -> List[BaseTool]:
        """Load MCP tools as LangChain tools."""
        try:
            if self.use_mcp_protocol:
                # Use new MCP protocol
                logger.info("Loading tools using MCP protocol")
                tools = self._load_mcp_protocol_tools()
            else:
                # Use legacy toolbox client
                logger.info("Loading tools using legacy toolbox client")
                tools = create_langchain_tools_sync(self.mcp_client, self.toolset_name)
            
            logger.info(f"Loaded {len(tools)} tools for Database Agent")
            return tools
        except Exception as e:
            logger.error(f"Failed to load tools: {e}")
            return []
    
    def _load_mcp_protocol_tools(self) -> List[BaseTool]:
        """Load tools using the new MCP protocol."""
        from langchain_core.tools import StructuredTool
        import asyncio
        
        # Get tools from MCP server
        try:
            if asyncio.iscoroutinefunction(self.mcp_client.list_tools):
                # Async client
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                mcp_tools = loop.run_until_complete(self.mcp_client.list_tools())
                loop.close()
            else:
                # Sync client
                mcp_tools = self.mcp_client.list_tools()
                
        except Exception as e:
            logger.error(f"Failed to list MCP tools: {e}")
            return []
        
        langchain_tools = []
        
        for mcp_tool in mcp_tools:
            def create_tool_function(tool_name: str):
                def tool_function(**kwargs) -> str:
                    """Execute MCP tool."""
                    try:
                        if asyncio.iscoroutinefunction(self.mcp_client.call_tool):
                            # Async client
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            result = loop.run_until_complete(
                                self.mcp_client.call_tool(tool_name, kwargs)
                            )
                            loop.close()
                        else:
                            # Sync client
                            result = self.mcp_client.call_tool(tool_name, kwargs)
                        
                        # Extract text content from MCP response
                        if isinstance(result, dict) and "content" in result:
                            content_items = result["content"]
                            if content_items and isinstance(content_items, list):
                                return content_items[0].get("text", str(result))
                        
                        return str(result)
                        
                    except Exception as e:
                        logger.error(f"Error executing tool {tool_name}: {e}")
                        return f"Error: {str(e)}"
                
                return tool_function
            
            # Create LangChain tool from MCP tool
            langchain_tool = StructuredTool.from_function(
                func=create_tool_function(mcp_tool.name),
                name=mcp_tool.name,
                description=mcp_tool.description,
                args_schema=None  # Could be enhanced to use mcp_tool.input_schema
            )
            
            langchain_tools.append(langchain_tool)
        
        return langchain_tools
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent executor."""
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            MessagesPlaceholder("chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder("agent_scratchpad"),
        ])
        
        # Create the agent
        agent = create_openai_tools_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            max_iterations=self.max_iterations,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=True
        )
        
        return agent_executor
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the database agent."""
        return """You are an intelligent database assistant powered by MCP Toolbox.
        
Your role is to help users interact with their database by:
1. Understanding natural language queries about data
2. Selecting the appropriate database tools to execute
3. Interpreting and presenting results in a clear, useful format
4. Providing insights and analysis when requested

Available capabilities:
- Search and filter data based on various criteria
- Perform analytics and generate reports
- Analyze trends and patterns in the data
- Provide summaries and insights

Guidelines:
- Always explain what you're going to do before executing database operations
- Present results in a clear, organized format
- When dealing with large datasets, provide summaries and highlights
- If a query is ambiguous, ask for clarification
- Suggest related queries or insights when appropriate
- Handle errors gracefully and explain what went wrong

Remember to be helpful, accurate, and transparent about the operations you're performing.
"""
    
    def query(
        self,
        question: str,
        chat_history: Optional[List[Union[HumanMessage, AIMessage]]] = None
    ) -> Dict[str, Any]:
        """
        Execute a natural language query against the database.
        
        Args:
            question: Natural language question about the data
            chat_history: Optional chat history for context
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            logger.info(f"Processing query: {question}")
            
            # Prepare input
            agent_input = {
                "input": question,
                "chat_history": chat_history or []
            }
            
            # Execute the agent
            result = self.agent_executor.invoke(agent_input)
            
            return {
                "answer": result.get("output", "No response generated"),
                "intermediate_steps": result.get("intermediate_steps", []),
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                "answer": f"I encountered an error while processing your query: {str(e)}",
                "intermediate_steps": [],
                "success": False,
                "error": str(e)
            }
    
    def analyze_data(
        self,
        analysis_request: str,
        include_visualizations: bool = False
    ) -> Dict[str, Any]:
        """
        Perform data analysis based on a natural language request.
        
        Args:
            analysis_request: Description of the analysis to perform
            include_visualizations: Whether to include visualization suggestions
            
        Returns:
            Dict containing analysis results and insights
        """
        enhanced_request = f"""
        Perform the following data analysis: {analysis_request}
        
        Please provide:
        1. The relevant data that addresses the analysis request
        2. Key insights and patterns you observe
        3. Statistical summaries where appropriate
        4. Recommendations or next steps based on the findings
        """
        
        if include_visualizations:
            enhanced_request += "\n5. Suggestions for visualizations that would help illustrate the findings"
        
        return self.query(enhanced_request)
    
    def search_data(
        self,
        search_criteria: str,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Search for specific data based on criteria.
        
        Args:
            search_criteria: Natural language description of what to search for
            limit: Optional limit on number of results
            
        Returns:
            Dict containing search results
        """
        search_query = f"Search for: {search_criteria}"
        
        if limit:
            search_query += f" (limit results to {limit} items)"
        
        return self.query(search_query)
    
    def get_summary(
        self,
        topic: str,
        time_period: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of data for a specific topic.
        
        Args:
            topic: Topic to summarize (e.g., "sales", "users", "orders")
            time_period: Optional time period (e.g., "last 30 days", "this month")
            
        Returns:
            Dict containing summary information
        """
        summary_query = f"Provide a summary of {topic}"
        
        if time_period:
            summary_query += f" for {time_period}"
        
        summary_query += ". Include key metrics, trends, and notable observations."
        
        return self.query(summary_query)
    
    def suggest_queries(self, context: str = "") -> List[str]:
        """
        Suggest useful queries based on available tools and context.
        
        Args:
            context: Optional context for suggestion
            
        Returns:
            List of suggested query strings
        """
        suggestions = [
            "Show me a summary of recent sales data",
            "Find users who haven't logged in recently",
            "What are the top-selling products this month?",
            "Analyze customer behavior patterns",
            "Check for any low stock items",
            "Show revenue breakdown by category",
            "Find the most active users",
            "Analyze trends in order patterns"
        ]
        
        # Filter suggestions based on available tools
        available_tools = [tool.name for tool in self.tools]
        
        # This could be enhanced to be more intelligent about suggestions
        # based on the actual tools available and the provided context
        
        return suggestions[:5]  # Return top 5 suggestions
    
    def reload_tools(self, toolset_name: Optional[str] = None):
        """
        Reload tools from MCP server.
        
        Args:
            toolset_name: Optional specific toolset to load
        """
        try:
            if toolset_name:
                self.toolset_name = toolset_name
            
            # Clear cache if available and reload tools
            if hasattr(self.mcp_client, 'clear_cache'):
                self.mcp_client.clear_cache()
            
            self.tools = self._load_tools()
            
            # Recreate agent with new tools
            self.agent_executor = self._create_agent()
            
            logger.info(f"Reloaded {len(self.tools)} tools")
            
        except Exception as e:
            logger.error(f"Failed to reload tools: {e}")
            raise
    
    def get_tool_info(self) -> List[Dict[str, str]]:
        """
        Get information about available tools.
        
        Returns:
            List of dictionaries with tool information
        """
        tool_info = []
        for tool in self.tools:
            tool_info.append({
                "name": tool.name,
                "description": tool.description,
                "type": type(tool).__name__
            })
        return tool_info
    
    async def store_extraction(
        self,
        url: str,
        title: str,
        content: str,
        extracted_data: dict,
        extraction_type: str,
        metadata: dict
    ) -> Any:
        """Store web extraction data (A2A method for Browserbase agent)."""
        try:
            # This method is called by other agents via A2A protocol
            logger.info(f"Storing extraction via A2A: {url}")
            
            # Use database tools to store the extraction
            storage_query = f"""
            Store the following web extraction data:
            URL: {url}
            Title: {title}
            Type: {extraction_type}
            Data: {self.json.dumps(extracted_data)}
            Metadata: {self.json.dumps(metadata)}
            """
            
            result = self.query(storage_query)
            
            if result.get("success"):
                logger.info(f"Extraction stored successfully via A2A")
                # Return a simple ID (could be enhanced to return actual DB ID)
                return len(str(extracted_data))  # Simple ID based on data size
            else:
                logger.error(f"Failed to store extraction: {result.get('error')}")
                raise Exception(f"Storage failed: {result.get('error')}")
        
        except Exception as e:
            logger.error(f"A2A storage error: {e}")
            raise
    
    async def execute_query(self, query: str, params: list = None) -> List[Dict[str, Any]]:
        """Execute database query (A2A method for other agents)."""
        try:
            logger.info(f"Executing query via A2A: {query[:100]}...")
            
            # Process the query through the agent
            if params:
                query_with_params = f"{query} Parameters: {params}"
            else:
                query_with_params = query
            
            result = self.query(query_with_params)
            
            if result.get("success"):
                # Return results in A2A format
                # This is a simplified response - could be enhanced
                return [{"status": "executed", "query": query, "params": params}]
            else:
                logger.error(f"Query execution failed: {result.get('error')}")
                return []
        
        except Exception as e:
            logger.error(f"A2A query execution error: {e}")
            return []
    
    async def register_with_hub(self) -> bool:
        """Register this agent with the central MCP hub."""
        try:
            import aiohttp
            
            registration_data = {
                "jsonrpc": "2.0",
                "id": str(self.uuid.uuid4()),
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "DatabaseAgent",
                    "agent_type": "data_storage",
                    "endpoint_url": f"http://localhost:{self.agent_port}",
                    "capabilities": [
                        {
                            "name": "store_extraction",
                            "description": "Store web extraction data in database",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "extracted_data": {"type": "object"},
                                    "extraction_type": {"type": "string"},
                                    "metadata": {"type": "object"}
                                },
                                "required": ["url", "title", "content", "extracted_data", "extraction_type"]
                            },
                            "output_schema": {
                                "type": "integer",
                                "description": "Extraction ID"
                            }
                        },
                        {
                            "name": "execute_query",
                            "description": "Execute database queries",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "query": {"type": "string"},
                                    "params": {"type": "array", "items": {"type": "string"}}
                                },
                                "required": ["query"]
                            },
                            "output_schema": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        },
                        {
                            "name": "query_data",
                            "description": "Natural language data queries",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "question": {"type": "string"}
                                },
                                "required": ["question"]
                            },
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "answer": {"type": "string"},
                                    "success": {"type": "boolean"}
                                }
                            }
                        },
                        {
                            "name": "analyze_data",
                            "description": "Perform data analysis",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "analysis_request": {"type": "string"},
                                    "include_visualizations": {"type": "boolean"}
                                },
                                "required": ["analysis_request"]
                            },
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "answer": {"type": "string"},
                                    "success": {"type": "boolean"}
                                }
                            }
                        }
                    ],
                    "metadata": {
                        "version": "1.0.0",
                        "description": "Database operations and analytics agent",
                        "supported_databases": ["postgresql", "sqlite", "mysql"]
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hub_url,
                    json=registration_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            self.registered_with_hub = True
                            logger.info(f"✅ Database agent registered with MCP Hub: {self.agent_id}")
                            
                            # Start heartbeat
                            self.heartbeat_task = asyncio.create_task(self._send_heartbeats())
                            
                            return True
                    
                    logger.error(f"Failed to register with hub: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Hub registration failed: {e}")
            return False
    
    async def _send_heartbeats(self):
        """Send periodic heartbeats to the hub."""
        try:
            import aiohttp
            
            while self.registered_with_hub:
                heartbeat_data = {
                    "jsonrpc": "2.0",
                    "id": str(self.uuid.uuid4()),
                    "method": "agents/heartbeat",
                    "params": {
                        "agent_id": self.agent_id,
                        "status": "active"
                    }
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.hub_url,
                            json=heartbeat_data,
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                logger.debug(f"Heartbeat sent successfully: {self.agent_id}")
                            else:
                                logger.warning(f"Heartbeat failed: {response.status}")
                
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                
                # Wait 30 seconds before next heartbeat
                await asyncio.sleep(30)
        
        except asyncio.CancelledError:
            logger.info("Database agent heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}")
    
    async def start_agent_server(self):
        """Start the agent's own MCP server for receiving calls."""
        try:
            from aiohttp import web
            import aiohttp_cors
            
            app = web.Application()
            
            # Setup CORS
            cors = aiohttp_cors.setup(app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Add MCP endpoint
            app.router.add_post('/mcp', self._handle_agent_request)
            
            # Add CORS
            for route in list(app.router.routes()):
                cors.add(route)
            
            # Start server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', self.agent_port)
            await site.start()
            
            logger.info(f"🚀 Database agent server started on port {self.agent_port}")
            return runner
        
        except Exception as e:
            logger.error(f"Failed to start agent server: {e}")
            return None
    
    async def _handle_agent_request(self, request):
        """Handle incoming MCP requests to this agent."""
        try:
            data = await request.json()
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Route to appropriate handler
            if method == "store_extraction":
                result = await self.store_extraction(
                    url=params.get("url"),
                    title=params.get("title"),
                    content=params.get("content"),
                    extracted_data=params.get("extracted_data"),
                    extraction_type=params.get("extraction_type"),
                    metadata=params.get("metadata", {})
                )
            elif method == "execute_query":
                result = await self.execute_query(
                    query=params.get("query"),
                    params=params.get("params")
                )
            elif method == "query_data":
                result = self.query(params.get("question"))
            elif method == "analyze_data":
                result = self.analyze_data(
                    analysis_request=params.get("analysis_request"),
                    include_visualizations=params.get("include_visualizations", False)
                )
            else:
                return self._agent_error_response(f"Unknown method: {method}", -32601, request_id)
            
            return self._agent_success_response(result, request_id)
        
        except Exception as e:
            logger.error(f"Error handling agent request: {e}")
            return self._agent_error_response(f"Internal error: {str(e)}", -32603)
    
    def _agent_success_response(self, result: Any, request_id: Optional[str] = None):
        """Create a JSON-RPC 2.0 success response."""
        from aiohttp import web
        
        response_data = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        if request_id is not None:
            response_data["id"] = request_id
        
        return web.json_response(response_data)
    
    def _agent_error_response(self, message: str, code: int = -32603, request_id: Optional[str] = None):
        """Create a JSON-RPC 2.0 error response."""
        from aiohttp import web
        
        response_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if request_id is not None:
            response_data["id"] = request_id
        
        return web.json_response(response_data, status=400 if code == -32600 else 200)
    
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        self.registered_with_hub = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Database agent {self.agent_id} shutdown complete")
    

class AsyncDatabaseAgent:
    """
    Async version of the Database Agent for use in async environments.
    """
    
    def __init__(self, *args, **kwargs):
        self._sync_agent = DatabaseAgent(*args, **kwargs)
    
    async def query(self, question: str, chat_history: Optional[List] = None) -> Dict[str, Any]:
        """Async wrapper for query method."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_agent.query, question, chat_history
        )
    
    async def analyze_data(self, analysis_request: str, include_visualizations: bool = False) -> Dict[str, Any]:
        """Async wrapper for analyze_data method."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_agent.analyze_data, analysis_request, include_visualizations
        )
    
    async def search_data(self, search_criteria: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """Async wrapper for search_data method."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_agent.search_data, search_criteria, limit
        )
    
    def get_tool_info(self) -> List[Dict[str, str]]:
        """Get tool information (no async needed)."""
        return self._sync_agent.get_tool_info()
    
    async def reload_tools(self, toolset_name: Optional[str] = None):
        """Async wrapper for reload_tools method."""
        import asyncio
        return await asyncio.get_event_loop().run_in_executor(
            None, self._sync_agent.reload_tools, toolset_name
        )
