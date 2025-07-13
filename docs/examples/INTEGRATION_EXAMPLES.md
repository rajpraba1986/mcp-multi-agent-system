# Quick Integration Examples

## Simple Data Extraction and Storage

This example demonstrates basic web data extraction and storage using the multi-agent system.

```python
import asyncio
import aiohttp
import json

class SimpleIntegrationExample:
    """Simple example of multi-agent integration."""
    
    def __init__(self):
        self.hub_url = "http://localhost:5000"
    
    async def extract_and_store_data(self, url: str, title: str) -> dict:
        """Extract data from a website and store it in the database."""
        
        print(f"🚀 Starting data extraction for: {url}")
        
        # Step 1: Discover available agents
        agents = await self._discover_agents()
        print(f"📋 Found {len(agents)} registered agents")
        
        # Step 2: Extract data using BrowserbaseAgent
        browserbase_agent = self._find_agent(agents, "web_automation")
        if not browserbase_agent:
            raise Exception("BrowserbaseAgent not available")
        
        extraction_result = await self._call_agent(
            browserbase_agent["endpoint_url"],
            "extract_website_data",
            {
                "url": url,
                "extraction_type": "article"
            }
        )
        
        print(f"✅ Data extracted: {len(extraction_result.get('content', ''))} characters")
        
        # Step 3: Store data using DatabaseAgent
        database_agent = self._find_agent(agents, "data_storage")
        if not database_agent:
            raise Exception("DatabaseAgent not available")
        
        storage_result = await self._call_agent(
            database_agent["endpoint_url"],
            "store_extraction",
            {
                "url": url,
                "title": title,
                "content": extraction_result.get("content", ""),
                "extracted_data": extraction_result,
                "extraction_type": "article",
                "metadata": {
                    "example_run": True,
                    "automation_level": "simple"
                }
            }
        )
        
        print(f"✅ Data stored with ID: {storage_result.get('id', 'unknown')}")
        
        return {
            "extraction": extraction_result,
            "storage": storage_result,
            "url": url,
            "title": title
        }
    
    async def query_stored_data(self, search_query: str) -> dict:
        """Query previously stored data."""
        
        print(f"🔍 Searching for: {search_query}")
        
        # Discover database agent
        agents = await self._discover_agents()
        database_agent = self._find_agent(agents, "data_storage")
        
        if not database_agent:
            raise Exception("DatabaseAgent not available")
        
        # Execute search
        search_result = await self._call_agent(
            database_agent["endpoint_url"],
            "query_data",
            {
                "query": f"Find content related to: {search_query}",
                "limit": 10
            }
        )
        
        print(f"✅ Found {len(search_result.get('results', []))} matching records")
        return search_result
    
    async def analyze_data(self, analysis_request: str) -> dict:
        """Analyze stored data using AI."""
        
        print(f"🧠 Analyzing: {analysis_request}")
        
        # Discover database agent
        agents = await self._discover_agents()
        database_agent = self._find_agent(agents, "data_storage")
        
        if not database_agent:
            raise Exception("DatabaseAgent not available")
        
        # Request analysis
        analysis_result = await self._call_agent(
            database_agent["endpoint_url"],
            "analyze_data",
            {
                "analysis_request": analysis_request,
                "include_visualizations": False
            }
        )
        
        print(f"✅ Analysis completed")
        return analysis_result
    
    # Helper methods
    async def _discover_agents(self) -> list:
        """Discover all registered agents."""
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.hub_url}/agents") as response:
                return await response.json()
    
    def _find_agent(self, agents: list, agent_type: str) -> dict:
        """Find a specific agent by type."""
        for agent in agents:
            if agent.get("agent_type") == agent_type:
                return agent
        return None
    
    async def _call_agent(self, endpoint_url: str, method: str, params: dict) -> dict:
        """Call a method on an agent."""
        request = {
            "jsonrpc": "2.0",
            "id": "example_request",
            "method": f"tools/call",
            "params": {
                "name": method,
                "arguments": params
            }
        }
        
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(endpoint_url, json=request) as response:
                result = await response.json()
                
                if "error" in result:
                    raise Exception(f"Agent call failed: {result['error']}")
                
                return result.get("result", {}).get("content", [{}])[0].get("text", {})

# Usage examples
async def main():
    """Main example function."""
    
    example = SimpleIntegrationExample()
    
    try:
        # Example 1: Extract and store data from a website
        print("=" * 60)
        print("Example 1: Web Data Extraction and Storage")
        print("=" * 60)
        
        result1 = await example.extract_and_store_data(
            url="https://example.com/article",
            title="Example Article"
        )
        
        print(f"📊 Extraction Summary:")
        print(f"   - URL: {result1['url']}")
        print(f"   - Content Length: {len(result1['extraction'].get('content', ''))}")
        print(f"   - Storage ID: {result1['storage'].get('id', 'N/A')}")
        
        # Example 2: Query stored data
        print("\n" + "=" * 60)
        print("Example 2: Data Query")
        print("=" * 60)
        
        search_result = await example.query_stored_data("article content")
        
        print(f"📋 Search Results:")
        for i, record in enumerate(search_result.get("results", [])[:3]):
            print(f"   {i+1}. {record.get('title', 'No Title')} - {record.get('url', 'No URL')}")
        
        # Example 3: Analyze data
        print("\n" + "=" * 60)
        print("Example 3: Data Analysis")
        print("=" * 60)
        
        analysis = await example.analyze_data(
            "Summarize the main topics and themes in the stored articles"
        )
        
        print(f"🧠 Analysis Result:")
        print(f"   {analysis.get('answer', 'No analysis available')[:200]}...")
        
    except Exception as e:
        print(f"❌ Example failed: {e}")
        print("Make sure all agents are running:")
        print("  - python agents/hub/hub.py")
        print("  - python agents/database_agent/database_agent.py")
        print("  - python agents/browserbase_agent/browserbase_agent.py")

if __name__ == "__main__":
    print("🚀 MCP Multi-Agent System - Integration Examples")
    print("Make sure the system is running before executing examples!")
    print()
    
    asyncio.run(main())
```

## Command-Line Quick Test

For a quick test without writing code, you can use curl or PowerShell:

### Test Agent Discovery

```powershell
# Check what agents are registered
$response = Invoke-RestMethod -Uri "http://localhost:5000/agents"
$response | ConvertTo-Json -Depth 3
```

### Test DatabaseAgent Directly

```powershell
# Test database query
$body = @{
    jsonrpc = "2.0"
    id = "test"
    method = "tools/call"
    params = @{
        name = "query_data"
        arguments = @{
            query = "Show me all stored data"
            limit = 5
        }
    }
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:8002/mcp" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 5
```

### Test BrowserbaseAgent

```powershell
# Test web data extraction
$body = @{
    jsonrpc = "2.0"
    id = "test"
    method = "tools/call"
    params = @{
        name = "extract_website_data"
        arguments = @{
            url = "https://example.com"
            extraction_type = "general"
        }
    }
} | ConvertTo-Json -Depth 3

$response = Invoke-RestMethod -Uri "http://localhost:8001/mcp" -Method Post -Body $body -ContentType "application/json"
$response | ConvertTo-Json -Depth 5
```

## Jupyter Notebook Integration

For interactive exploration, you can use the system in a Jupyter notebook:

```python
# Cell 1: Setup
import asyncio
import aiohttp
import json
from IPython.display import display, HTML, JSON

# Cell 2: Define helper functions
async def discover_agents():
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:5000/agents") as response:
            return await response.json()

async def call_agent(endpoint, method, params):
    request = {
        "jsonrpc": "2.0",
        "id": "notebook_request",
        "method": "tools/call",
        "params": {
            "name": method,
            "arguments": params
        }
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(endpoint, json=request) as response:
            return await response.json()

# Cell 3: Discover agents
agents = await discover_agents()
display(JSON(agents))

# Cell 4: Extract web data
extraction_result = await call_agent(
    "http://localhost:8001/mcp",
    "extract_website_data",
    {"url": "https://news.ycombinator.com", "extraction_type": "general"}
)
display(JSON(extraction_result))

# Cell 5: Store the data
storage_result = await call_agent(
    "http://localhost:8002/mcp",
    "store_extraction",
    {
        "url": "https://news.ycombinator.com",
        "title": "Hacker News Front Page",
        "content": extraction_result["result"]["content"][0]["text"]["content"],
        "extraction_type": "news"
    }
)
display(JSON(storage_result))
```

## Error Handling Best Practices

```python
import asyncio
import aiohttp
import logging

class RobustAgentCaller:
    """Robust agent calling with error handling and retries."""
    
    def __init__(self, max_retries=3, timeout=30):
        self.max_retries = max_retries
        self.timeout = timeout
    
    async def call_agent_with_retry(self, endpoint_url, method, params):
        """Call agent with retry logic and error handling."""
        
        for attempt in range(self.max_retries):
            try:
                request = {
                    "jsonrpc": "2.0",
                    "id": f"request_{attempt}",
                    "method": "tools/call",
                    "params": {
                        "name": method,
                        "arguments": params
                    }
                }
                
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(endpoint_url, json=request) as response:
                        
                        if response.status == 200:
                            result = await response.json()
                            
                            if "error" in result:
                                error_msg = result["error"].get("message", "Unknown error")
                                logging.error(f"Agent error: {error_msg}")
                                
                                # Some errors are worth retrying
                                if "timeout" in error_msg.lower() or "busy" in error_msg.lower():
                                    if attempt < self.max_retries - 1:
                                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                        continue
                                
                                raise Exception(f"Agent error: {error_msg}")
                            
                            return result.get("result", {})
                        
                        else:
                            logging.warning(f"HTTP {response.status} on attempt {attempt + 1}")
                            if attempt < self.max_retries - 1:
                                await asyncio.sleep(2 ** attempt)
                                continue
                            else:
                                raise Exception(f"HTTP error: {response.status}")
            
            except asyncio.TimeoutError:
                logging.warning(f"Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise Exception("Request timed out after all retry attempts")
            
            except Exception as e:
                logging.error(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                else:
                    raise

# Usage
async def robust_example():
    caller = RobustAgentCaller(max_retries=3, timeout=30)
    
    try:
        result = await caller.call_agent_with_retry(
            "http://localhost:8001/mcp",
            "extract_website_data",
            {"url": "https://example.com"}
        )
        print("✅ Success:", result)
    
    except Exception as e:
        print("❌ Failed after all retries:", e)

# Run the robust example
asyncio.run(robust_example())
```

---

**These examples provide a foundation for integrating the MCP Multi-Agent System into your applications and workflows.**
