#!/usr/bin/env python3
"""
Custom email client for the email agent with different protocol
"""

import aiohttp
import json
import uuid
from typing import Dict, Any, Optional

class EmailAgentClient:
    """Custom client for email agent with /mcp/request endpoint"""
    
    def __init__(self, server_url: str):
        self.server_url = server_url
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def send_extraction_notification(self, extracted_data: list, total_extractions: int, extraction_summary: str) -> Any:
        """Send extraction notification email"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "send_extraction_notification",
            "params": {
                "extracted_data": extracted_data,
                "total_extractions": total_extractions,
                "extraction_summary": extraction_summary
            }
        }
        
        try:
            async with self._session.post(
                f"{self.server_url}/mcp/request",
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
    
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
