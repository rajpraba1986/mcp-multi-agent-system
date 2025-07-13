#!/usr/bin/env python3
"""
MCP Hub Architecture Implementation

A central MCP hub that agents register with and discover each other through.
Agents expose their capabilities as MCP servers while consuming others' capabilities as clients.
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, asdict
from aiohttp import web, ClientSession, ClientTimeout
import aiohttp_cors
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class AgentCapability:
    """Represents a capability that an agent provides."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]

@dataclass
class RegisteredAgent:
    """Represents an agent registered with the hub."""
    agent_id: str
    agent_name: str
    agent_type: str
    endpoint_url: str
    capabilities: List[AgentCapability]
    registered_at: datetime
    last_heartbeat: datetime
    status: str = "active"  # active, inactive, error
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

@dataclass
class HubStats:
    """Hub statistics and health information."""
    total_agents: int
    active_agents: int
    inactive_agents: int
    total_capabilities: int
    total_requests: int
    hub_started_at: datetime
    uptime_seconds: float

class MCPHub:
    """
    Central MCP Hub for agent registration, discovery, and coordination.
    
    The hub provides:
    1. Agent registration and discovery
    2. Capability registry
    3. Message routing between agents
    4. Health monitoring and heartbeats
    5. Load balancing for agent calls
    """
    
    def __init__(self, host: str = "localhost", port: int = 5000):
        self.host = host
        self.port = port
        self.started_at = datetime.now()
        
        # Agent registry
        self.registered_agents: Dict[str, RegisteredAgent] = {}
        self.capability_index: Dict[str, List[str]] = {}  # capability_name -> [agent_ids]
        
        # Statistics
        self.request_count = 0
        self.heartbeat_interval = 30  # seconds
        self.agent_timeout = 90  # seconds
        
        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None
        self.app = None
        
        logger.info(f"MCP Hub initialized on {host}:{port}")
    
    async def start(self):
        """Start the MCP Hub server."""
        # Create aiohttp application
        self.app = web.Application()
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Register routes
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/health', self.handle_health_check)
        self.app.router.add_get('/stats', self.handle_stats)
        self.app.router.add_get('/agents', self.handle_list_agents)
        
        # Add CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self.cleanup_inactive_agents())
        
        # Start server
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        
        logger.info(f"🚀 MCP Hub started on http://{self.host}:{self.port}")
        logger.info("📋 Available endpoints:")
        logger.info("   POST /mcp - MCP protocol endpoint")
        logger.info("   GET  /health - Health check")
        logger.info("   GET  /stats - Hub statistics")
        logger.info("   GET  /agents - List registered agents")
        
        return runner
    
    async def handle_mcp_request(self, request):
        """Handle incoming MCP protocol requests."""
        try:
            data = await request.json()
            self.request_count += 1
            
            # Validate JSON-RPC 2.0 format
            if not self._validate_json_rpc(data):
                return self._error_response("Invalid JSON-RPC 2.0 format", -32600)
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Route to appropriate handler
            if method == "agents/register":
                result = await self._handle_agent_registration(params)
            elif method == "agents/discover":
                result = await self._handle_agent_discovery(params)
            elif method == "agents/heartbeat":
                result = await self._handle_heartbeat(params)
            elif method == "capabilities/discover":
                result = await self._handle_capability_discovery(params)
            elif method == "agents/call":
                result = await self._handle_agent_call(params)
            elif method == "tools/list":
                result = await self._handle_list_tools(params)
            elif method == "tools/call":
                result = await self._handle_tool_call(params)
            else:
                return self._error_response(f"Unknown method: {method}", -32601, request_id)
            
            return self._success_response(result, request_id)
            
        except json.JSONDecodeError:
            return self._error_response("Invalid JSON", -32700)
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}")
            return self._error_response(f"Internal error: {str(e)}", -32603)
    
    async def _handle_agent_registration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent registration."""
        agent_id = params.get("agent_id")
        agent_name = params.get("agent_name")
        agent_type = params.get("agent_type", "generic")
        endpoint_url = params.get("endpoint_url")
        capabilities = params.get("capabilities", [])
        metadata = params.get("metadata", {})
        
        if not all([agent_id, agent_name, endpoint_url]):
            raise ValueError("Missing required fields: agent_id, agent_name, endpoint_url")
        
        # Convert capabilities to objects
        capability_objects = []
        for cap in capabilities:
            if isinstance(cap, dict):
                capability_objects.append(AgentCapability(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    input_schema=cap.get("input_schema", {}),
                    output_schema=cap.get("output_schema", {})
                ))
        
        # Register agent
        registered_agent = RegisteredAgent(
            agent_id=agent_id,
            agent_name=agent_name,
            agent_type=agent_type,
            endpoint_url=endpoint_url,
            capabilities=capability_objects,
            registered_at=datetime.now(),
            last_heartbeat=datetime.now(),
            metadata=metadata
        )
        
        self.registered_agents[agent_id] = registered_agent
        
        # Update capability index
        for capability in capability_objects:
            if capability.name not in self.capability_index:
                self.capability_index[capability.name] = []
            if agent_id not in self.capability_index[capability.name]:
                self.capability_index[capability.name].append(agent_id)
        
        logger.info(f"✅ Agent registered: {agent_name} ({agent_id}) with {len(capability_objects)} capabilities")
        
        return {
            "agent_id": agent_id,
            "status": "registered",
            "hub_endpoint": f"http://{self.host}:{self.port}/mcp",
            "heartbeat_interval": self.heartbeat_interval,
            "registered_at": registered_agent.registered_at.isoformat()
        }
    
    async def _handle_agent_discovery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent discovery requests."""
        agent_type_filter = params.get("agent_type")
        capability_filter = params.get("capability")
        status_filter = params.get("status", "active")
        
        agents = []
        for agent_id, agent in self.registered_agents.items():
            # Apply filters
            if status_filter and agent.status != status_filter:
                continue
            if agent_type_filter and agent.agent_type != agent_type_filter:
                continue
            if capability_filter:
                agent_capabilities = [cap.name for cap in agent.capabilities]
                if capability_filter not in agent_capabilities:
                    continue
            
            agents.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_type": agent.agent_type,
                "endpoint_url": agent.endpoint_url,
                "capabilities": [asdict(cap) for cap in agent.capabilities],
                "status": agent.status,
                "last_heartbeat": agent.last_heartbeat.isoformat(),
                "metadata": agent.metadata
            })
        
        return {
            "agents": agents,
            "total_count": len(agents),
            "filters_applied": {
                "agent_type": agent_type_filter,
                "capability": capability_filter,
                "status": status_filter
            }
        }
    
    async def _handle_heartbeat(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent heartbeat."""
        agent_id = params.get("agent_id")
        status = params.get("status", "active")
        
        if agent_id not in self.registered_agents:
            raise ValueError(f"Agent not registered: {agent_id}")
        
        # Update heartbeat
        self.registered_agents[agent_id].last_heartbeat = datetime.now()
        self.registered_agents[agent_id].status = status
        
        return {
            "agent_id": agent_id,
            "heartbeat_received": True,
            "status": status,
            "next_heartbeat_due": (datetime.now() + timedelta(seconds=self.heartbeat_interval)).isoformat()
        }
    
    async def _handle_capability_discovery(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle capability discovery."""
        capability_name = params.get("capability_name")
        
        if capability_name and capability_name in self.capability_index:
            agent_ids = self.capability_index[capability_name]
            providers = []
            for agent_id in agent_ids:
                if agent_id in self.registered_agents:
                    agent = self.registered_agents[agent_id]
                    if agent.status == "active":
                        providers.append({
                            "agent_id": agent.agent_id,
                            "agent_name": agent.agent_name,
                            "endpoint_url": agent.endpoint_url
                        })
            
            return {
                "capability_name": capability_name,
                "providers": providers,
                "provider_count": len(providers)
            }
        else:
            # Return all capabilities
            all_capabilities = {}
            for agent in self.registered_agents.values():
                if agent.status == "active":
                    for cap in agent.capabilities:
                        if cap.name not in all_capabilities:
                            all_capabilities[cap.name] = []
                        all_capabilities[cap.name].append({
                            "agent_id": agent.agent_id,
                            "agent_name": agent.agent_name,
                            "endpoint_url": agent.endpoint_url,
                            "description": cap.description
                        })
            
            return {
                "all_capabilities": all_capabilities,
                "capability_count": len(all_capabilities)
            }
    
    async def _handle_agent_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle agent-to-agent calls through the hub."""
        target_agent_id = params.get("target_agent_id")
        method = params.get("method")
        call_params = params.get("params", {})
        
        if target_agent_id not in self.registered_agents:
            raise ValueError(f"Target agent not found: {target_agent_id}")
        
        target_agent = self.registered_agents[target_agent_id]
        if target_agent.status != "active":
            raise ValueError(f"Target agent not active: {target_agent_id}")
        
        # Forward the call to the target agent
        async with ClientSession(timeout=ClientTimeout(total=30)) as session:
            mcp_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": method,
                "params": call_params
            }
            
            try:
                async with session.post(
                    f"{target_agent.endpoint_url}/mcp",
                    json=mcp_request,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result
                    else:
                        raise Exception(f"Agent call failed with status {response.status}")
            
            except Exception as e:
                logger.error(f"Failed to call agent {target_agent_id}: {e}")
                # Mark agent as potentially inactive
                target_agent.status = "error"
                raise
    
    async def _handle_list_tools(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool listing requests."""
        all_tools = []
        
        for agent in self.registered_agents.values():
            if agent.status == "active":
                for capability in agent.capabilities:
                    all_tools.append({
                        "name": capability.name,
                        "description": capability.description,
                        "input_schema": capability.input_schema,
                        "output_schema": capability.output_schema,
                        "provider_agent": {
                            "agent_id": agent.agent_id,
                            "agent_name": agent.agent_name,
                            "endpoint_url": agent.endpoint_url
                        }
                    })
        
        return {
            "tools": all_tools,
            "tool_count": len(all_tools)
        }
    
    async def _handle_tool_call(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle tool execution requests."""
        tool_name = params.get("tool_name")
        tool_params = params.get("params", {})
        
        # Find agent that provides this tool
        if tool_name not in self.capability_index:
            raise ValueError(f"Tool not found: {tool_name}")
        
        agent_ids = self.capability_index[tool_name]
        active_agents = [
            self.registered_agents[agent_id] 
            for agent_id in agent_ids 
            if agent_id in self.registered_agents and self.registered_agents[agent_id].status == "active"
        ]
        
        if not active_agents:
            raise ValueError(f"No active agents provide tool: {tool_name}")
        
        # Use first active agent (could implement load balancing here)
        target_agent = active_agents[0]
        
        # Forward the tool call
        return await self._handle_agent_call({
            "target_agent_id": target_agent.agent_id,
            "method": "tools/call",
            "params": {
                "tool_name": tool_name,
                "params": tool_params
            }
        })
    
    async def handle_health_check(self, request):
        """Handle health check requests."""
        stats = self._get_hub_stats()
        
        health_data = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": stats.uptime_seconds,
            "active_agents": stats.active_agents,
            "total_agents": stats.total_agents
        }
        
        return web.json_response(health_data)
    
    async def handle_stats(self, request):
        """Handle statistics requests."""
        stats = self._get_hub_stats()
        return web.json_response(asdict(stats), default=str)
    
    async def handle_list_agents(self, request):
        """Handle agent listing requests."""
        agents = []
        for agent in self.registered_agents.values():
            agents.append({
                "agent_id": agent.agent_id,
                "agent_name": agent.agent_name,
                "agent_type": agent.agent_type,
                "status": agent.status,
                "capabilities": [cap.name for cap in agent.capabilities],
                "last_heartbeat": agent.last_heartbeat.isoformat()
            })
        
        return web.json_response({
            "agents": agents,
            "total_count": len(agents)
        })
    
    async def cleanup_inactive_agents(self):
        """Background task to cleanup inactive agents."""
        while True:
            try:
                current_time = datetime.now()
                inactive_agents = []
                
                for agent_id, agent in self.registered_agents.items():
                    time_since_heartbeat = (current_time - agent.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.agent_timeout:
                        inactive_agents.append(agent_id)
                        agent.status = "inactive"
                        logger.warning(f"Agent {agent.agent_name} ({agent_id}) marked as inactive - no heartbeat for {time_since_heartbeat}s")
                
                # Remove inactive agents from capability index
                for agent_id in inactive_agents:
                    for capability_name, provider_list in self.capability_index.items():
                        if agent_id in provider_list:
                            provider_list.remove(agent_id)
                
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(self.heartbeat_interval)
    
    def _get_hub_stats(self) -> HubStats:
        """Get current hub statistics."""
        active_agents = sum(1 for agent in self.registered_agents.values() if agent.status == "active")
        inactive_agents = len(self.registered_agents) - active_agents
        total_capabilities = sum(len(agent.capabilities) for agent in self.registered_agents.values())
        uptime = (datetime.now() - self.started_at).total_seconds()
        
        return HubStats(
            total_agents=len(self.registered_agents),
            active_agents=active_agents,
            inactive_agents=inactive_agents,
            total_capabilities=total_capabilities,
            total_requests=self.request_count,
            hub_started_at=self.started_at,
            uptime_seconds=uptime
        )
    
    def _validate_json_rpc(self, data: Dict[str, Any]) -> bool:
        """Validate JSON-RPC 2.0 format."""
        return (
            isinstance(data, dict) and
            data.get("jsonrpc") == "2.0" and
            "method" in data
        )
    
    def _success_response(self, result: Any, request_id: Optional[str] = None) -> web.Response:
        """Create a JSON-RPC 2.0 success response."""
        response_data = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        if request_id is not None:
            response_data["id"] = request_id
        
        return web.json_response(response_data)
    
    def _error_response(self, message: str, code: int = -32603, request_id: Optional[str] = None) -> web.Response:
        """Create a JSON-RPC 2.0 error response."""
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
    
    async def stop(self):
        """Stop the hub and cleanup."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MCP Hub stopped")

async def main():
    """Example usage of the MCP Hub."""
    hub = MCPHub(host="localhost", port=5000)
    
    try:
        runner = await hub.start()
        print("🚀 MCP Hub is running!")
        print(f"📍 Hub endpoint: http://localhost:5000/mcp")
        print(f"🏥 Health check: http://localhost:5000/health")
        print(f"📊 Statistics: http://localhost:5000/stats")
        print(f"👥 Agents list: http://localhost:5000/agents")
        print("\nPress Ctrl+C to stop...")
        
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping MCP Hub...")
    finally:
        await hub.stop()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
