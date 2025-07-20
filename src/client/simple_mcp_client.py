#!/usr/bin/env python3
"""
Simple MCP Client for testing extraction workflows.
Bypasses complex dataclass issues.
"""

import asyncio
import aiohttp
import json
import uuid
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

class SimpleMCPClient:
    """Simple MCP client for testing workflows."""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Call a tool using simple HTTP requests."""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            async with self._session.post(
                f"{self.server_url}/mcp",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {})
                else:
                    return {"status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def test_connection(self) -> bool:
        """Test connection to server."""
        try:
            if not self._session:
                self._session = aiohttp.ClientSession()
            
            request_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "ping",
                "params": {}
            }
            
            async with self._session.post(
                f"{self.server_url}/mcp",
                json=request_data,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {}).get("status") == "ok"
                else:
                    return False
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    async def close(self):
        """Close the session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

# Alias for compatibility
MCPClient = SimpleMCPClient
