# Adding New Agents to the MCP Multi-Agent System

## Overview

This guide shows you how to create and integrate new agents into the MCP multi-agent system. The architecture is designed for **easy expansion** - you can add agents without modifying existing ones.

## 🏗️ Agent Template

### 1. Basic Agent Structure

Create your new agent file: `src/agents/your_agent.py`

```python
"""
Your Custom Agent for MCP Multi-Agent System.
"""

import asyncio
import logging
import os
import uuid
import json
from typing import Dict, List, Optional, Any, Union

from langchain_core.language_models import BaseLanguageModel
from langchain_anthropic import ChatAnthropic

from ..client.mcp_client import MCPProtocolClient, MCPToolboxClient
from ..utils.config import ConfigManager
from ..utils.llm_factory import create_llm_from_config

logger = logging.getLogger(__name__)


class YourCustomAgent:
    """
    Description of what your agent does.
    
    Example: File processing agent that handles document conversion,
    text extraction, and metadata analysis.
    """
    
    def __init__(
        self,
        mcp_client: Union[MCPProtocolClient, MCPToolboxClient],
        llm: Optional[BaseLanguageModel] = None,
        temperature: float = 0.1,
        agent_port: int = 8004,  # Choose unique port
        hub_url: str = "http://localhost:5000/mcp"
    ):
        """
        Initialize Your Custom Agent.
        
        Args:
            mcp_client: MCP client instance
            llm: Language model (defaults to Anthropic Claude)
            temperature: LLM temperature for response generation
            agent_port: Port for this agent's MCP server
            hub_url: URL of the central MCP hub
        """
        self.mcp_client = mcp_client
        self.temperature = temperature
        self.agent_port = agent_port
        self.hub_url = hub_url
        self.agent_id = f"your-agent-{uuid.uuid4().hex[:8]}"
        
        # Hub integration
        self.registered_with_hub = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Store for later use
        self.uuid = uuid
        self.json = json
        
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
                # Fallback to direct initialization
                self.llm = ChatAnthropic(
                    model="claude-3-haiku-20240307",
                    temperature=temperature,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    streaming=True
                )
        else:
            self.llm = llm
        
        logger.info(f"Initialized {self.__class__.__name__}: {self.agent_id}")
    
    # ===== A2A METHODS (called by other agents) =====
    
    async def your_main_capability(
        self, 
        input_param: str, 
        options: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Your agent's primary capability (A2A method).
        
        This method will be called by other agents via A2A communication.
        
        Args:
            input_param: Main input parameter
            options: Optional configuration parameters
            
        Returns:
            Dict with processing results
        """
        try:
            logger.info(f"Processing {input_param} via A2A")
            
            # Your agent's core logic here
            # Example: Process files, analyze data, make API calls, etc.
            
            result = {
                "status": "completed",
                "input": input_param,
                "processed_data": f"Processed: {input_param}",
                "timestamp": "2025-07-12T10:00:00Z",
                "agent_id": self.agent_id
            }
            
            logger.info(f"A2A processing complete: {input_param}")
            return result
            
        except Exception as e:
            logger.error(f"A2A processing error: {e}")
            raise
    
    async def secondary_capability(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Secondary capability (A2A method).
        
        Args:
            data: Input data to process
            
        Returns:
            List of processed results
        """
        try:
            logger.info(f"Secondary processing via A2A")
            
            # Secondary processing logic
            results = [
                {"item": i, "processed": True, "data": data}
                for i in range(3)
            ]
            
            return results
            
        except Exception as e:
            logger.error(f"A2A secondary processing error: {e}")
            raise
    
    # ===== HUB INTEGRATION =====
    
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
                    "agent_name": "YourCustomAgent",
                    "agent_type": "your_agent_type",  # e.g., "file_processing", "integration", etc.
                    "endpoint_url": f"http://localhost:{self.agent_port}",
                    "capabilities": [
                        {
                            "name": "your_main_capability",
                            "description": "Description of your main capability",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "input_param": {"type": "string"},
                                    "options": {"type": "object"}
                                },
                                "required": ["input_param"]
                            },
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "status": {"type": "string"},
                                    "processed_data": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "secondary_capability",
                            "description": "Description of secondary capability",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "object"}
                                },
                                "required": ["data"]
                            },
                            "output_schema": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        }
                    ],
                    "metadata": {
                        "version": "1.0.0",
                        "description": "Your agent description for discovery",
                        "supported_formats": ["pdf", "docx", "txt"]  # Example metadata
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
                            logger.info(f"✅ {self.__class__.__name__} registered with MCP Hub: {self.agent_id}")
                            
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
            logger.info(f"{self.__class__.__name__} heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}")
    
    # ===== AGENT SERVER =====
    
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
            
            logger.info(f"🚀 {self.__class__.__name__} server started on port {self.agent_port}")
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
            if method == "your_main_capability":
                result = await self.your_main_capability(
                    input_param=params.get("input_param"),
                    options=params.get("options", {})
                )
            elif method == "secondary_capability":
                result = await self.secondary_capability(
                    data=params.get("data")
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
    
    # ===== LIFECYCLE MANAGEMENT =====
    
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        self.registered_with_hub = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"{self.__class__.__name__} {self.agent_id} shutdown complete")


# ===== ASYNC WRAPPER (if needed) =====

class AsyncYourCustomAgent:
    """
    Async version of YourCustomAgent for use in async environments.
    Only needed if you have sync methods that need async wrappers.
    """
    
    def __init__(self, *args, **kwargs):
        self._sync_agent = YourCustomAgent(*args, **kwargs)
    
    async def your_main_capability(self, input_param: str, options: Dict = None) -> Dict[str, Any]:
        """Async wrapper for main capability."""
        return await self._sync_agent.your_main_capability(input_param, options)
    
    async def secondary_capability(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Async wrapper for secondary capability."""
        return await self._sync_agent.secondary_capability(data)
```

### 2. Agent Registration Script

Create `examples/run_your_agent_example.py`:

```python
"""
Example script to run Your Custom Agent.
"""

import asyncio
import logging
import os
from src.agents.your_agent import YourCustomAgent
from src.client.mcp_client import MCPProtocolClient

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run Your Custom Agent example."""
    
    try:
        # Create MCP client
        mcp_client = MCPProtocolClient()
        
        # Initialize your agent
        your_agent = YourCustomAgent(
            mcp_client=mcp_client,
            agent_port=8004,  # Choose unique port
            temperature=0.1
        )
        
        # Register with hub
        logger.info("Registering with MCP Hub...")
        registration_success = await your_agent.register_with_hub()
        
        if not registration_success:
            logger.error("Failed to register with hub")
            return
        
        # Start agent server
        logger.info("Starting agent server...")
        runner = await your_agent.start_agent_server()
        
        if not runner:
            logger.error("Failed to start agent server")
            return
        
        logger.info("✅ Your Custom Agent is running!")
        logger.info(f"   Agent ID: {your_agent.agent_id}")
        logger.info(f"   Port: {your_agent.agent_port}")
        logger.info(f"   Endpoint: http://localhost:{your_agent.agent_port}/mcp")
        
        # Test the agent's capabilities
        logger.info("\n🧪 Testing agent capabilities...")
        
        # Test main capability
        test_result = await your_agent.your_main_capability(
            input_param="test_input",
            options={"test_mode": True}
        )
        logger.info(f"Test result: {test_result}")
        
        # Keep running
        logger.info("\n⚡ Agent is ready for A2A communication...")
        logger.info("Press Ctrl+C to stop")
        
        # Wait indefinitely
        await asyncio.Event().wait()
        
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down agent...")
        await your_agent.shutdown()
        if runner:
            await runner.cleanup()
        logger.info("✅ Agent shutdown complete")
    
    except Exception as e:
        logger.error(f"Error running agent: {e}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 🔗 Integration with Existing Agents

### 1. Add to Orchestration Workflows

Update `examples/agent_orchestration_workflow.py`:

```python
class AgentOrchestrator:
    # ... existing code ...
    
    async def your_agent_workflow(
        self, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Workflow involving your new agent.
        """
        workflow_id = f"your_workflow_{uuid.uuid4().hex[:8]}"
        results = {"workflow_id": workflow_id, "steps": []}
        
        try:
            # Step 1: Discover your agent
            logger.info("Step 1: Discovering your custom agent")
            your_agent = await self._discover_agent("your_agent_type")
            
            if not your_agent:
                raise Exception("Your custom agent not available")
            
            # Step 2: Call your agent's main capability
            main_result = await self._call_agent(
                your_agent["endpoint_url"],
                "your_main_capability",
                {
                    "input_param": input_data.get("input"),
                    "options": input_data.get("options", {})
                }
            )
            
            results["steps"].append({
                "step": 1,
                "action": "main_processing",
                "status": "completed",
                "agent": "your_custom_agent",
                "result": main_result
            })
            
            # Step 3: Use secondary capability
            secondary_result = await self._call_agent(
                your_agent["endpoint_url"],
                "secondary_capability",
                {
                    "data": main_result
                }
            )
            
            results["steps"].append({
                "step": 2,
                "action": "secondary_processing",
                "status": "completed",
                "agent": "your_custom_agent",
                "result": secondary_result
            })
            
            # Step 4: Store results in database (optional)
            database_agent = await self._discover_agent("data_storage")
            if database_agent:
                await self._call_agent(
                    database_agent["endpoint_url"],
                    "store_extraction",
                    {
                        "url": "internal://your-agent-workflow",
                        "title": f"Workflow Results {workflow_id}",
                        "content": str(secondary_result),
                        "extracted_data": {
                            "workflow_id": workflow_id,
                            "main_result": main_result,
                            "secondary_result": secondary_result
                        },
                        "extraction_type": "workflow_result",
                        "metadata": {"timestamp": "2025-07-12T10:00:00Z"}
                    }
                )
            
            results["status"] = "completed"
            results["message"] = "Your agent workflow completed successfully"
            
        except Exception as e:
            logger.error(f"Your agent workflow error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results
```

### 2. Called by Other Agents

Example of how existing agents can call your new agent:

```python
# In BrowserbaseAgent
class BrowserbaseAgent:
    async def extract_and_process_with_your_agent(self, url: str):
        """Extract web data and process with your custom agent."""
        
        # Extract web data
        extraction_data = await self.extract_website_data(url)
        
        # Discover your agent
        your_agent = await self._discover_agent("your_agent_type")
        
        if your_agent:
            # Call your agent to process the extracted data
            processed_result = await self._call_agent(
                your_agent["endpoint_url"],
                "your_main_capability",
                {
                    "input_param": extraction_data["content"],
                    "options": {
                        "source_url": url,
                        "extraction_type": extraction_data["type"]
                    }
                }
            )
            
            return processed_result
```

## 📊 Agent Type Categories

Choose the appropriate agent type for hub registration:

| Agent Type | Purpose | Example Agents |
|------------|---------|----------------|
| `file_processing` | File operations and conversions | PDFAgent, ImageAgent, DocumentAgent |
| `integration` | External service integration | CRMAgent, ERPAgent, APIGatewayAgent |
| `ai_analysis` | Advanced AI processing | SentimentAgent, ClassificationAgent, SummaryAgent |
| `communication` | Messaging and notifications | EmailAgent, SlackAgent, SMSAgent |
| `monitoring` | System monitoring and alerts | HealthAgent, MetricsAgent, LogAgent |
| `data_processing` | Data transformation and ETL | CleansingAgent, ValidationAgent, TransformAgent |
| `web_automation` | Web scraping and automation | BrowserbaseAgent, ScrapingAgent |
| `data_storage` | Database operations | DatabaseAgent, CacheAgent |

## 🧪 Testing Your New Agent

### 1. Unit Tests

Create `tests/test_your_agent.py`:

```python
"""
Tests for Your Custom Agent.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock

from src.agents.your_agent import YourCustomAgent
from src.client.mcp_client import MCPProtocolClient


@pytest.fixture
async def your_agent():
    """Create a test instance of your agent."""
    mock_client = MagicMock(spec=MCPProtocolClient)
    agent = YourCustomAgent(
        mcp_client=mock_client,
        agent_port=8999  # Use test port
    )
    yield agent
    await agent.shutdown()


@pytest.mark.asyncio
async def test_main_capability(your_agent):
    """Test the main capability."""
    result = await your_agent.your_main_capability(
        input_param="test_input",
        options={"test": True}
    )
    
    assert result["status"] == "completed"
    assert result["input"] == "test_input"
    assert "processed_data" in result


@pytest.mark.asyncio
async def test_secondary_capability(your_agent):
    """Test the secondary capability."""
    test_data = {"test": "data"}
    result = await your_agent.secondary_capability(test_data)
    
    assert isinstance(result, list)
    assert len(result) > 0
    assert all(item["processed"] for item in result)


@pytest.mark.asyncio
async def test_agent_registration(your_agent):
    """Test agent registration with hub."""
    # Mock aiohttp response
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {"result": {"status": "registered"}}
        mock_post.return_value.__aenter__.return_value = mock_response
        
        success = await your_agent.register_with_hub()
        assert success
        assert your_agent.registered_with_hub
```

### 2. Integration Tests

Create `tests/test_your_agent_integration.py`:

```python
"""
Integration tests for Your Custom Agent.
"""

import pytest
import asyncio
import aiohttp
from unittest.mock import patch

from src.agents.your_agent import YourCustomAgent
from src.client.mcp_client import MCPProtocolClient


@pytest.mark.asyncio
async def test_a2a_communication():
    """Test A2A communication with your agent."""
    
    # Start your agent
    mock_client = MagicMock(spec=MCPProtocolClient)
    agent = YourCustomAgent(mock_client, agent_port=8998)
    
    try:
        # Start server
        runner = await agent.start_agent_server()
        
        # Test A2A call
        async with aiohttp.ClientSession() as session:
            request_data = {
                "jsonrpc": "2.0",
                "method": "your_main_capability",
                "params": {
                    "input_param": "test_a2a",
                    "options": {"test": True}
                },
                "id": "test-123"
            }
            
            async with session.post(
                f"http://localhost:8998/mcp",
                json=request_data
            ) as response:
                assert response.status == 200
                result = await response.json()
                
                assert result["jsonrpc"] == "2.0"
                assert result["id"] == "test-123"
                assert "result" in result
                assert result["result"]["status"] == "completed"
        
    finally:
        await agent.shutdown()
        if runner:
            await runner.cleanup()
```

## 🚀 Deployment

### 1. Add to Docker Compose (if using containers)

```yaml
# docker-compose.yml
services:
  your-custom-agent:
    build: .
    command: python examples/run_your_agent_example.py
    ports:
      - "8004:8004"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    depends_on:
      - mcp-hub
    networks:
      - mcp-network
```

### 2. Add to Process Manager

```python
# process_manager.py
async def start_all_agents():
    """Start all agents in the system."""
    
    agents = [
        ("DatabaseAgent", 8002, "run_database_agent.py"),
        ("BrowserbaseAgent", 8001, "run_browserbase_example.py"),
        ("EmailAgent", 8003, "run_email_agent.py"),
        ("YourCustomAgent", 8004, "run_your_agent_example.py"),  # Add your agent
    ]
    
    for name, port, script in agents:
        await start_agent(name, port, script)
```

## 🎯 Best Practices

### 1. Agent Design Principles

- **Single Responsibility**: Each agent should have a clear, focused purpose
- **Stateless Operations**: Avoid maintaining state between requests
- **Error Resilience**: Handle errors gracefully and provide meaningful error messages
- **Idempotent Operations**: Operations should be safe to retry
- **Resource Cleanup**: Properly cleanup resources on shutdown

### 2. A2A Method Design

```python
async def your_capability(self, param1: str, param2: Dict = None) -> Dict[str, Any]:
    """
    Good A2A method design:
    - Clear parameter types
    - Optional parameters with defaults
    - Structured return values
    - Comprehensive error handling
    """
    try:
        # Validate inputs
        if not param1:
            raise ValueError("param1 is required")
        
        # Process with progress logging
        logger.info(f"Processing {param1}")
        
        # Return structured data
        return {
            "status": "success",
            "input": param1,
            "result": "processed_data",
            "timestamp": datetime.utcnow().isoformat(),
            "agent_id": self.agent_id
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        # Re-raise for A2A error handling
        raise
```

### 3. Configuration Management

```python
# Use environment variables for configuration
class YourCustomAgent:
    def __init__(self, ...):
        # Agent-specific configuration
        self.batch_size = int(os.getenv("YOUR_AGENT_BATCH_SIZE", "10"))
        self.timeout = int(os.getenv("YOUR_AGENT_TIMEOUT", "30"))
        self.external_api_key = os.getenv("YOUR_AGENT_API_KEY")
        
        if not self.external_api_key:
            raise ValueError("YOUR_AGENT_API_KEY environment variable required")
```

### 4. Documentation

Always include comprehensive docstrings:

```python
class YourCustomAgent:
    """
    Your Custom Agent for specific functionality.
    
    This agent provides:
    - Feature 1: Description
    - Feature 2: Description
    - Feature 3: Description
    
    A2A Methods:
    - your_main_capability: Primary processing function
    - secondary_capability: Secondary processing function
    
    Configuration:
    - YOUR_AGENT_API_KEY: Required API key
    - YOUR_AGENT_BATCH_SIZE: Processing batch size (default: 10)
    
    Example Usage:
        agent = YourCustomAgent(mcp_client, agent_port=8004)
        await agent.register_with_hub()
        await agent.start_agent_server()
    """
```

---

**Following this template ensures your new agent integrates seamlessly with the existing multi-agent ecosystem while maintaining consistency and reliability.**
