# Database Agent Usage Guide

## Overview

The DatabaseAgent is an intelligent database operations agent that uses **Anthropic Claude LLM** to understand natural language queries and execute appropriate database operations through MCP tools.

## 🧠 Core Capabilities

### Natural Language Database Queries

The DatabaseAgent can understand and process natural language requests:

```python
# Example natural language queries
queries = [
    "Show me all users who registered in the last 30 days",
    "What are the top 5 selling products this month?",
    "Find customers with orders over $1000",
    "Analyze sales trends by region",
    "Count active users by subscription type"
]

for query in queries:
    result = database_agent.query(query)
    print(f"Query: {query}")
    print(f"Answer: {result['answer']}")
```

### Data Analysis & Insights

```python
# Perform complex data analysis
analysis_result = database_agent.analyze_data(
    analysis_request="Analyze customer churn patterns over the last quarter",
    include_visualizations=True
)

print(f"Analysis: {analysis_result['answer']}")
```

### A2A Method Capabilities

Other agents can call DatabaseAgent methods directly:

| Method | Purpose | Example Usage |
|--------|---------|---------------|
| `store_extraction` | Store web extraction data | Called by BrowserbaseAgent |
| `execute_query` | Run SQL queries | Called by ReportingAgent |
| `query_data` | Natural language queries | Called by ChatbotAgent |
| `analyze_data` | Data analysis & insights | Called by AnalyticsAgent |

## 🚀 Initialization & Setup

### Basic Setup

```python
import asyncio
from src.agents.database_agent import DatabaseAgent
from src.client.mcp_client import MCPProtocolClient

async def setup_database_agent():
    # Create MCP client
    mcp_client = MCPProtocolClient()
    
    # Initialize Database Agent
    database_agent = DatabaseAgent(
        mcp_client=mcp_client,
        temperature=0.1,           # LLM temperature
        max_iterations=5,          # Max agent iterations
        agent_port=8002,          # Agent server port
        hub_url="http://localhost:5000/mcp"  # Hub URL
    )
    
    # Register with hub for A2A communication
    await database_agent.register_with_hub()
    
    # Start agent server
    await database_agent.start_agent_server()
    
    return database_agent
```

### Environment Configuration

Ensure your `.env` file contains:

```env
# LLM Configuration
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Optional: Override default settings
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-haiku-20240307
LLM_TEMPERATURE=0.1

# Database Configuration (if using MCP database tools)
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

## 📊 Usage Examples

### 1. Simple Database Query

```python
# Ask a question about your data
result = database_agent.query("How many users do we have?")

if result['success']:
    print(f"Answer: {result['answer']}")
    
    # View intermediate steps
    for step in result['intermediate_steps']:
        print(f"Step: {step}")
else:
    print(f"Error: {result['error']}")
```

### 2. Data Search with Criteria

```python
# Search for specific data
search_result = database_agent.search_data(
    search_criteria="users who haven't logged in for 30 days",
    limit=50
)

print(f"Found: {search_result['answer']}")
```

### 3. Topic Summary

```python
# Get a summary of specific data
summary = database_agent.get_summary(
    topic="sales performance",
    time_period="last quarter"
)

print(f"Summary: {summary['answer']}")
```

### 4. Complex Data Analysis

```python
# Perform detailed analysis
analysis = database_agent.analyze_data(
    analysis_request="""
    Analyze our e-commerce data to identify:
    1. Customer segments with highest lifetime value
    2. Products with declining sales trends
    3. Seasonal patterns in purchasing behavior
    4. Correlation between marketing campaigns and sales
    """,
    include_visualizations=True
)

print(f"Analysis Results: {analysis['answer']}")
```

## 🔄 Agent-to-Agent Integration

### Called by BrowserbaseAgent

```python
# BrowserbaseAgent automatically calls DatabaseAgent
class BrowserbaseAgent:
    async def extract_website_data(self, url, store_in_database=True):
        # ... extraction logic ...
        
        if store_in_database:
            # A2A call to DatabaseAgent
            database_agent_url = "http://localhost:8002/mcp"
            storage_result = await self._call_agent(
                database_agent_url,
                "store_extraction",
                {
                    "url": url,
                    "title": extracted_title,
                    "content": extracted_content,
                    "extracted_data": structured_data,
                    "extraction_type": "webpage",
                    "metadata": {"timestamp": "2025-07-12T10:00:00Z"}
                }
            )
```

### Called by EmailAgent for Data-Driven Notifications

```python
# EmailAgent queries DatabaseAgent for data
class EmailAgent:
    async def send_analytics_report(self, recipient):
        # Query database for latest analytics
        database_agent_url = "http://localhost:8002/mcp"
        analytics_data = await self._call_agent(
            database_agent_url,
            "analyze_data",
            {
                "analysis_request": "Generate weekly business intelligence summary",
                "include_visualizations": False
            }
        )
        
        # Send email with analytics
        await self.send_notification(
            recipient=recipient,
            subject="Weekly Analytics Report",
            body=f"Analytics Summary:\n{analytics_data['answer']}"
        )
```

## 🛠️ Advanced Configuration

### Custom Tool Loading

```python
# Load specific tool sets
database_agent = DatabaseAgent(
    mcp_client=mcp_client,
    toolset_name="postgres_tools",  # Load only PostgreSQL tools
    use_mcp_protocol=True          # Use new MCP protocol
)

# Reload tools dynamically
database_agent.reload_tools("mysql_tools")
```

### Custom LLM Configuration

```python
from langchain_anthropic import ChatAnthropic

# Use custom LLM instance
custom_llm = ChatAnthropic(
    model="claude-3-sonnet-20240229",  # More powerful model
    temperature=0.0,                   # Deterministic responses
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    max_tokens=4000
)

database_agent = DatabaseAgent(
    mcp_client=mcp_client,
    llm=custom_llm  # Use custom LLM
)
```

### Agent Server Configuration

```python
# Configure agent server settings
database_agent = DatabaseAgent(
    mcp_client=mcp_client,
    agent_port=8010,                    # Custom port
    hub_url="http://hub.company.com",   # Production hub
    max_iterations=10                   # More complex reasoning
)
```

## 📈 Performance Optimization

### Query Optimization Tips

1. **Be Specific**: More specific queries get better results
   ```python
   # Good
   "Show sales for Q4 2024 grouped by product category"
   
   # Less optimal
   "Show me some sales data"
   ```

2. **Use Context**: Provide relevant context in queries
   ```python
   result = database_agent.query(
       "Compare current month sales to last month",
       chat_history=[
           HumanMessage(content="I'm looking at e-commerce performance"),
           AIMessage(content="I'll help you analyze e-commerce sales data")
       ]
   )
   ```

3. **Limit Large Results**: Use limits for large datasets
   ```python
   result = database_agent.search_data(
       "all customer orders",
       limit=100  # Prevent overwhelming responses
   )
   ```

### Tool Management

```python
# Check available tools
tool_info = database_agent.get_tool_info()
for tool in tool_info:
    print(f"Tool: {tool['name']} - {tool['description']}")

# Get suggested queries based on available tools
suggestions = database_agent.suggest_queries("e-commerce analytics")
for suggestion in suggestions:
    print(f"Suggested: {suggestion}")
```

## 🔍 Troubleshooting

### Common Issues & Solutions

**1. Agent Won't Start**
```python
# Check if port is available
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8002))
if result == 0:
    print("Port 8002 is already in use")
```

**2. LLM Authentication Fails**
```python
# Verify API key
import os
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    print("ANTHROPIC_API_KEY not set in environment")
elif len(api_key) < 10:
    print("ANTHROPIC_API_KEY appears to be invalid")
```

**3. No Tools Loaded**
```python
# Check tool loading
if len(database_agent.tools) == 0:
    print("No tools loaded - check MCP client connection")
    # Try reloading
    database_agent.reload_tools()
```

**4. A2A Communication Fails**
```python
# Test agent endpoint
import aiohttp
async def test_agent_endpoint():
    async with aiohttp.ClientSession() as session:
        test_request = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": "test"
        }
        async with session.post(
            "http://localhost:8002/mcp",
            json=test_request
        ) as response:
            print(f"Agent response: {response.status}")
```

### Debug Mode

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Create agent with verbose output
database_agent = DatabaseAgent(
    mcp_client=mcp_client,
    max_iterations=3,  # Reduce for debugging
)

# Query with detailed output
result = database_agent.query("test query")
print(f"Intermediate steps: {result['intermediate_steps']}")
```

## 🎯 Best Practices

### Query Design

1. **Structure Complex Requests**
   ```python
   analysis_request = """
   Please analyze our customer data and provide:
   1. Customer segmentation by purchase behavior
   2. Identify high-value customers (top 20%)
   3. Recommend retention strategies for each segment
   4. Suggest products for cross-selling opportunities
   """
   
   result = database_agent.analyze_data(analysis_request)
   ```

2. **Use Follow-up Questions**
   ```python
   # Initial query
   result1 = database_agent.query("What are our top products?")
   
   # Follow-up with context
   result2 = database_agent.query(
       "For these top products, show me the sales trend over the last 6 months",
       chat_history=[
           HumanMessage(content="What are our top products?"),
           AIMessage(content=result1['answer'])
       ]
   )
   ```

### Error Handling

```python
async def safe_database_query(agent, query, max_retries=3):
    """Safely execute database query with retry logic."""
    
    for attempt in range(max_retries):
        try:
            result = agent.query(query)
            
            if result['success']:
                return result
            else:
                print(f"Attempt {attempt + 1} failed: {result['error']}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1} error: {e}")
            
        if attempt < max_retries - 1:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
    
    return {"success": False, "error": "Max retries exceeded"}
```

### Resource Management

```python
# Proper agent lifecycle management
class DatabaseAgentManager:
    def __init__(self):
        self.agent = None
        self.server_runner = None
    
    async def start(self):
        """Start the database agent."""
        self.agent = await setup_database_agent()
        self.server_runner = await self.agent.start_agent_server()
        
    async def stop(self):
        """Gracefully shutdown the agent."""
        if self.agent:
            await self.agent.shutdown()
        if self.server_runner:
            await self.server_runner.cleanup()

# Usage
async def main():
    manager = DatabaseAgentManager()
    try:
        await manager.start()
        
        # Use the agent
        result = manager.agent.query("Show me recent data")
        print(result['answer'])
        
    finally:
        await manager.stop()
```

---

**The DatabaseAgent provides a powerful interface for natural language database operations while maintaining the flexibility to integrate with other agents in complex workflows.**
