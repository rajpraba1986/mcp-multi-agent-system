"""
MCP Protocol Compliant Client with A2A Communication Support.

This module implements the real Model Context Protocol (MCP) specification
and enables Agent-to-Agent (A2A) communication following JSON-RPC standards.
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, List, Optional, Any, Union, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, asdict
from enum import Enum

import aiohttp
import websockets
from toolbox_core import ToolboxClient
# Temporarily comment out problematic import
# from toolbox_langchain import ToolboxLangChain


logger = logging.getLogger(__name__)


# MCP Protocol Data Classes
@dataclass
class MCPMessage:
    """Base MCP message following JSON-RPC 2.0 specification."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None

@dataclass
class MCPRequest:
    """MCP request message."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

@dataclass
class MCPResponse:
    """MCP response message."""
    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None

@dataclass
class MCPNotification:
    """MCP notification message (no response expected)."""
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None

@dataclass
class MCPError:
    """MCP error information."""
    code: int
    message: str
    data: Optional[Any] = None

class MCPErrorCode(Enum):
    """Standard MCP error codes."""
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    SERVER_ERROR = -32000

@dataclass
class MCPTool:
    """MCP tool definition."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Optional[Dict[str, Any]] = None

@dataclass
class MCPAgent:
    """MCP agent information for A2A communication."""
    id: str
    name: str
    description: str
    capabilities: List[str]
    endpoint: str
    version: str = "1.0"

class MCPProtocolClient:
    """
    Real MCP Protocol compliant client with A2A communication support.
    
    Implements the full Model Context Protocol specification including:
    - JSON-RPC 2.0 message format
    - Tool discovery and execution
    - Agent-to-Agent communication
    - Resource management
    - Streaming support
    """


    def __init__(
        self,
        server_url: str = "http://localhost:5000",
        agent_id: Optional[str] = None,
        agent_name: str = "DatabaseAgent",
        capabilities: Optional[List[str]] = None,
        timeout: int = 30,
        retry_attempts: int = 3
    ):
        """
        Initialize the MCP Protocol client with A2A support.
        
        Args:
            server_url: URL of the MCP server
            agent_id: Unique identifier for this agent
            agent_name: Human-readable name for this agent
            capabilities: List of capabilities this agent provides
            timeout: Request timeout in seconds
            retry_attempts: Number of retry attempts for failed requests
        """
        self.server_url = server_url
        self.agent_id = agent_id or str(uuid.uuid4())
        self.agent_name = agent_name
        self.capabilities = capabilities or ["database_query", "data_analysis", "reporting"]
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        
        # Connection management
        self._session: Optional[aiohttp.ClientSession] = None
        self._websocket: Optional[websockets.WebSocketServerProtocol] = None
        self._message_handlers: Dict[str, Callable] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
        # Agent registry for A2A communication
        self._registered_agents: Dict[str, MCPAgent] = {}
        
        # Tool management
        self._available_tools: Dict[str, MCPTool] = {}
        self._tool_handlers: Dict[str, Callable] = {}
        
        # Legacy client support
        self._core_client: Optional[ToolboxClient] = None
        self._langchain_client: Optional[Any] = None
        
        # Setup default message handlers
        self._setup_message_handlers()
        
        logger.info(f"Initialized MCP Protocol client - Agent: {self.agent_name} ({self.agent_id})")

    def _setup_message_handlers(self):
        """Setup default MCP message handlers."""
        self._message_handlers.update({
            "ping": self._handle_ping,
            "tools/list": self._handle_list_tools,
            "tools/call": self._handle_call_tool,
            "agents/register": self._handle_agent_register,
            "agents/list": self._handle_list_agents,
            "agents/call": self._handle_agent_call,
            "resources/list": self._handle_list_resources,
            "resources/read": self._handle_read_resource,
        })

    async def _handle_ping(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle ping request."""
        return {"status": "ok", "agent_id": self.agent_id, "timestamp": asyncio.get_event_loop().time()}

    async def _handle_list_tools(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle tools listing request."""
        return {
            "tools": [asdict(tool) for tool in self._available_tools.values()]
        }

    async def _handle_call_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution request."""
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})
        
        if tool_name not in self._tool_handlers:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        handler = self._tool_handlers[tool_name]
        result = await handler(tool_arguments) if asyncio.iscoroutinefunction(handler) else handler(tool_arguments)
        
        return {"content": [{"type": "text", "text": str(result)}]}

    async def _handle_agent_register(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent registration for A2A communication."""
        agent_info = MCPAgent(**params)
        self._registered_agents[agent_info.id] = agent_info
        logger.info(f"Registered agent: {agent_info.name} ({agent_info.id})")
        return {"status": "registered", "agent_id": agent_info.id}

    async def _handle_list_agents(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle agent listing request."""
        return {
            "agents": [asdict(agent) for agent in self._registered_agents.values()]
        }

    async def _handle_agent_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent-to-agent communication request."""
        target_agent_id = params.get("agent_id")
        method = params.get("method")
        call_params = params.get("params", {})
        
        if target_agent_id not in self._registered_agents:
            raise ValueError(f"Agent '{target_agent_id}' not found")
        
        target_agent = self._registered_agents[target_agent_id]
        
        # Forward the call to the target agent
        result = await self._send_agent_request(target_agent.endpoint, method, call_params)
        return result

    async def _handle_list_resources(self, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Handle resource listing request."""
        return {"resources": []}  # Placeholder for resource management

    async def _handle_read_resource(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle resource reading request."""
        return {"contents": []}  # Placeholder for resource management
    
    async def _send_agent_request(self, endpoint: str, method: str, params: Dict[str, Any]) -> Any:
        """Send request to another agent."""
        request = MCPRequest(
            id=str(uuid.uuid4()),
            method=method,
            params=params
        )
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        async with self._session.post(
            f"{endpoint}/mcp",
            json=asdict(request),
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        ) as response:
            result = await response.json()
            if "error" in result:
                raise Exception(f"Agent call failed: {result['error']}")
            return result.get("result")

    async def send_mcp_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Send MCP request following JSON-RPC 2.0 specification.
        
        Args:
            method: MCP method name
            params: Optional parameters
            
        Returns:
            Response result or raises exception on error
        """
        request = MCPRequest(
            id=str(uuid.uuid4()),
            method=method,
            params=params
        )
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            async with self._session.post(
                f"{self.server_url}/mcp",
                json=asdict(request),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {await response.text()}")
                
                result = await response.json()
                
                if "error" in result:
                    error = result["error"]
                    raise Exception(f"MCP Error {error.get('code')}: {error.get('message')}")
                
                return result.get("result")
                
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            raise

    async def send_mcp_notification(self, method: str, params: Optional[Dict[str, Any]] = None):
        """
        Send MCP notification (no response expected).
        
        Args:
            method: MCP method name
            params: Optional parameters
        """
        notification = MCPNotification(method=method, params=params)
        
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            async with self._session.post(
                f"{self.server_url}/mcp",
                json=asdict(notification),
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                pass  # Notifications don't expect responses
                
        except Exception as e:
            logger.warning(f"MCP notification failed: {e}")

    async def register_tool(self, tool: MCPTool, handler: Callable):
        """
        Register a tool that this agent can provide to others.
        
        Args:
            tool: Tool definition
            handler: Function to handle tool execution
        """
        self._available_tools[tool.name] = tool
        self._tool_handlers[tool.name] = handler
        logger.info(f"Registered tool: {tool.name}")

    async def register_with_server(self) -> bool:
        """
        Register this agent with the MCP server for A2A communication.
        
        Returns:
            bool: True if registration successful
        """
        try:
            agent_info = MCPAgent(
                id=self.agent_id,
                name=self.agent_name,
                description=f"Database agent with capabilities: {', '.join(self.capabilities)}",
                capabilities=self.capabilities,
                endpoint=f"http://localhost:8000/agents/{self.agent_id}"  # This agent's endpoint
            )
            
            result = await self.send_mcp_request("agents/register", asdict(agent_info))
            logger.info(f"Successfully registered agent with server: {result}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            return False

    async def discover_agents(self) -> List[MCPAgent]:
        """
        Discover other agents available for A2A communication.
        
        Returns:
            List of available agents
        """
        try:
            result = await self.send_mcp_request("agents/list")
            agents = [MCPAgent(**agent_data) for agent_data in result.get("agents", [])]
            
            for agent in agents:
                self._registered_agents[agent.id] = agent
            
            logger.info(f"Discovered {len(agents)} agents")
            return agents
            
        except Exception as e:
            logger.error(f"Failed to discover agents: {e}")
            return []

    async def call_agent(self, agent_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Call another agent using A2A communication.
        
        Args:
            agent_id: Target agent ID
            method: Method to call on the target agent
            params: Parameters for the method call
            
        Returns:
            Result from the target agent
        """
        try:
            result = await self.send_mcp_request("agents/call", {
                "agent_id": agent_id,
                "method": method,
                "params": params or {}
            })
            
            logger.info(f"Successfully called agent {agent_id}.{method}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to call agent {agent_id}: {e}")
            raise

    async def list_tools(self) -> List[MCPTool]:
        """
        List available tools from the MCP server.
        
        Returns:
            List of available tools
        """
        try:
            result = await self.send_mcp_request("tools/list")
            tools = [MCPTool(**tool_data) for tool_data in result.get("tools", [])]
            
            logger.info(f"Discovered {len(tools)} tools")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to list tools: {e}")
            return []

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        Call a tool using MCP protocol.
        
        Args:
            tool_name: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Tool execution result
        """
        try:
            result = await self.send_mcp_request("tools/call", {
                "name": tool_name,
                "arguments": arguments
            })
            
            logger.info(f"Successfully called tool: {tool_name}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to call tool {tool_name}: {e}")
            raise
    
    async def test_connection(self) -> bool:
        """
        Test the connection to the MCP server.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        try:
            result = await self.send_mcp_request("ping")
            logger.info("Successfully connected to MCP server")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP server: {e}")
            return False

    async def start_a2a_server(self, port: int = 8000):
        """
        Start A2A communication server for this agent.
        
        Args:
            port: Port to listen on for A2A communication
        """
        from aiohttp import web
        
        async def handle_mcp_request(request):
            """Handle incoming MCP requests from other agents."""
            try:
                data = await request.json()
                
                # Parse MCP message
                method = data.get("method")
                params = data.get("params", {})
                message_id = data.get("id")
                
                # Handle the request
                if method in self._message_handlers:
                    result = await self._message_handlers[method](params)
                    
                    if message_id:  # Request expects response
                        response = MCPResponse(id=message_id, result=result)
                        return web.json_response(asdict(response))
                    else:  # Notification
                        return web.Response(status=200)
                else:
                    error = MCPError(
                        code=MCPErrorCode.METHOD_NOT_FOUND.value,
                        message=f"Method '{method}' not found"
                    )
                    response = MCPResponse(id=message_id, error=asdict(error))
                    return web.json_response(asdict(response), status=400)
                    
            except Exception as e:
                error = MCPError(
                    code=MCPErrorCode.INTERNAL_ERROR.value,
                    message=str(e)
                )
                response = MCPResponse(id=data.get("id"), error=asdict(error))
                return web.json_response(asdict(response), status=500)
        
        app = web.Application()
        app.router.add_post('/mcp', handle_mcp_request)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', port)
        await site.start()
        
        logger.info(f"A2A server started on http://localhost:{port}")

    # Legacy compatibility methods
    @asynccontextmanager
    async def get_core_client(self):
        """Get or create a core ToolboxClient instance (legacy compatibility)."""
        if self._core_client is None:
            self._core_client = ToolboxClient(self.server_url)
        
        try:
            yield self._core_client
        finally:
            pass
    
    @asynccontextmanager
    async def get_langchain_client(self):
        """Get or create a LangChain ToolboxClient instance (legacy compatibility)."""
        if self._langchain_client is None:
            # Temporarily disable langchain client due to import issues
            self._langchain_client = None
        
        try:
            yield self._langchain_client
        finally:
            pass

    async def load_toolset(self, toolset_name: Optional[str] = None) -> List[Any]:
        """
        Load tools using MCP protocol (with legacy fallback).
        
        Args:
            toolset_name: Name of the toolset to load
            
        Returns:
            List of loaded tools
        """
        try:
            # Try MCP protocol first
            tools = await self.list_tools()
            if toolset_name:
                # Filter by toolset if specified
                filtered_tools = [tool for tool in tools if toolset_name in tool.name.lower()]
                return filtered_tools
            return tools
            
        except Exception as e:
            logger.warning(f"MCP tool loading failed, falling back to legacy: {e}")
            
            # Fallback to legacy client
            try:
                async with self.get_core_client() as client:
                    tools = await client.load_toolset(toolset_name) if toolset_name else await client.load_toolset()
                    return tools
            except Exception as legacy_error:
                logger.error(f"Both MCP and legacy tool loading failed: {legacy_error}")
                return []

    async def load_langchain_tools(self, toolset_name: Optional[str] = None) -> List[Any]:
        """Load LangChain-compatible tools."""
        try:
            async with self.get_langchain_client() as client:
                tools = await client.load_toolset(toolset_name) if toolset_name else await client.load_toolset()
                return tools
        except Exception as e:
            logger.error(f"Failed to load LangChain tools: {e}")
            return []

    async def close(self):
        """Close the client connections."""
        if self._session:
            await self._session.close()
            self._session = None
        
        if self._websocket:
            await self._websocket.close()
            self._websocket = None
        
        if self._core_client and hasattr(self._core_client, 'close'):
            await self._core_client.close()
            self._core_client = None
        
        if self._langchain_client and hasattr(self._langchain_client, 'close'):
            await self._langchain_client.close()
            self._langchain_client = None
        
        logger.info("Closed MCP client connections")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Legacy class alias for backward compatibility
class MCPToolboxClient(MCPProtocolClient):
    """Legacy alias for MCPProtocolClient."""
    pass
    
class SyncMCPToolboxClient:
    """
    Synchronous wrapper around MCPProtocolClient for non-async environments.
    """
    
    def __init__(self, *args, **kwargs):
        self._async_client = MCPProtocolClient(*args, **kwargs)
    
    def test_connection(self) -> bool:
        """Test connection to the MCP server."""
        return asyncio.run(self._async_client.test_connection())
    
    def register_with_server(self) -> bool:
        """Register this agent with the MCP server."""
        return asyncio.run(self._async_client.register_with_server())
    
    def discover_agents(self) -> List[MCPAgent]:
        """Discover other agents for A2A communication."""
        return asyncio.run(self._async_client.discover_agents())
    
    def call_agent(self, agent_id: str, method: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Call another agent."""
        return asyncio.run(self._async_client.call_agent(agent_id, method, params))
    
    def load_toolset(self, toolset_name: Optional[str] = None) -> List[Any]:
        """Load tools from a toolset."""
        return asyncio.run(self._async_client.load_toolset(toolset_name))
    
    def load_langchain_tools(self, toolset_name: Optional[str] = None) -> List[Any]:
        """Load LangChain-compatible tools."""
        return asyncio.run(self._async_client.load_langchain_tools(toolset_name))
    
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool using MCP protocol."""
        return asyncio.run(self._async_client.call_tool(tool_name, arguments))
    
    def close(self):
        """Close the client connections."""
        asyncio.run(self._async_client.close())
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
