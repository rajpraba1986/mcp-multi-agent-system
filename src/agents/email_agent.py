"""
Email Agent for MCP Toolbox Integration.
Example of how to add a new agent to the ecosystem.
"""

import logging
import asyncio
import os
from typing import Dict, List, Optional, Any, Union
import uuid
import json

from langchain_core.language_models import BaseLanguageModel
from langchain_anthropic import ChatAnthropic

from ..client.mcp_client import MCPProtocolClient, MCPToolboxClient
from ..utils.config import ConfigManager
from ..utils.llm_factory import create_llm_from_config

logger = logging.getLogger(__name__)


class EmailAgent:
    """
    Email processing agent that can send notifications and process email data.
    Demonstrates how new agents integrate with the existing ecosystem.
    """
    
    def __init__(
        self,
        mcp_client: Union[MCPProtocolClient, MCPToolboxClient],
        llm: Optional[BaseLanguageModel] = None,
        temperature: float = 0.1,
        hub_url: str = "http://localhost:5000/mcp",
        agent_port: int = 8003  # Different port for each agent
    ):
        self.mcp_client = mcp_client
        self.temperature = temperature
        self.hub_url = hub_url
        self.agent_port = agent_port
        self.agent_id = f"email-agent-{uuid.uuid4().hex[:8]}"
        
        # Initialize LLM (same pattern as other agents)
        if llm is None:
            try:
                config_manager = ConfigManager()
                self.llm = create_llm_from_config(
                    config_manager=config_manager,
                    temperature=temperature
                )
            except Exception as e:
                logger.warning(f"Failed to load configuration, using default Anthropic Claude: {e}")
                self.llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=temperature,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    streaming=True
                )
        else:
            self.llm = llm
        
        self.registered_with_hub = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        logger.info(f"Initialized Email Agent: {self.agent_id}")
    
    # A2A Methods that other agents can call
    async def send_notification(self, recipient: str, subject: str, 
                               body: str, priority: str = "normal") -> Dict[str, Any]:
        """Send email notification (A2A method for other agents)."""
        try:
            logger.info(f"Sending notification via A2A: {subject}")
            
            # Email sending logic would go here
            # For demo purposes, we'll simulate success
            notification_id = f"email_{uuid.uuid4().hex[:8]}"
            
            return {
                "notification_id": notification_id,
                "status": "sent",
                "recipient": recipient,
                "subject": subject,
                "priority": priority
            }
        
        except Exception as e:
            logger.error(f"A2A notification error: {e}")
            raise
    
    async def process_email_data(self, email_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and analyze email data (A2A method)."""
        try:
            logger.info(f"Processing email data via A2A")
            
            # Email processing logic
            processed_data = {
                "processed_at": "2025-07-12T10:00:00Z",
                "sentiment": "neutral",
                "category": "business",
                "priority_score": 0.7,
                "extracted_entities": ["meeting", "deadline", "project"]
            }
            
            return processed_data
        
        except Exception as e:
            logger.error(f"A2A email processing error: {e}")
            raise
    
    async def register_with_hub(self) -> bool:
        """Register this agent with the central MCP hub."""
        try:
            import aiohttp
            
            registration_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "EmailAgent",
                    "agent_type": "communication",  # Different type
                    "endpoint_url": f"http://localhost:{self.agent_port}",
                    "capabilities": [
                        {
                            "name": "send_notification",
                            "description": "Send email notifications",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "recipient": {"type": "string"},
                                    "subject": {"type": "string"},
                                    "body": {"type": "string"},
                                    "priority": {"type": "string", "enum": ["low", "normal", "high"]}
                                },
                                "required": ["recipient", "subject", "body"]
                            }
                        },
                        {
                            "name": "process_email_data",
                            "description": "Process and analyze email content",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "email_data": {"type": "object"}
                                },
                                "required": ["email_data"]
                            }
                        }
                    ],
                    "metadata": {
                        "version": "1.0.0",
                        "description": "Email processing and notification agent"
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
                        self.registered_with_hub = True
                        logger.info(f"✅ Email agent registered with MCP Hub: {self.agent_id}")
                        return True
            
            return False
        
        except Exception as e:
            logger.error(f"Hub registration failed: {e}")
            return False
    
    async def start_agent_server(self):
        """Start the agent's own MCP server."""
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
            
            app.router.add_post('/mcp', self._handle_agent_request)
            
            for route in list(app.router.routes()):
                cors.add(route)
            
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', self.agent_port)
            await site.start()
            
            logger.info(f"🚀 Email agent server started on port {self.agent_port}")
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
            
            if method == "send_notification":
                result = await self.send_notification(
                    recipient=params.get("recipient"),
                    subject=params.get("subject"),
                    body=params.get("body"),
                    priority=params.get("priority", "normal")
                )
            elif method == "process_email_data":
                result = await self.process_email_data(
                    email_data=params.get("email_data")
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
