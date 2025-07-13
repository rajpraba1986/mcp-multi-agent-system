#!/usr/bin/env python3
"""
MCP Protocol and A2A Communication Example.

This example demonstrates the real MCP protocol implementation
and Agent-to-Agent communication capabilities.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from client.mcp_client import MCPProtocolClient, MCPTool, MCPAgent
from agents.database_agent import DatabaseAgent
from utils.logging import setup_logging
from utils.config import ConfigManager

# Setup logging
setup_logging(level="INFO")
logger = logging.getLogger(__name__)

async def demonstrate_mcp_protocol():
    """Demonstrate MCP protocol compliance and features."""
    print("\n🚀 MCP Protocol Demonstration")
    print("=" * 50)
    
    # Create MCP client with agent information
    client = MCPProtocolClient(
        server_url="http://localhost:5000",
        agent_name="DemoAgent",
        capabilities=["database_query", "data_analysis", "reporting"]
    )
    
    print(f"✅ Created MCP client: {client.agent_name} ({client.agent_id})")
    
    try:
        # Test connection
        print("\n🔍 Testing connection to MCP server...")
        if await client.test_connection():
            print("✅ Successfully connected to MCP server")
        else:
            print("⚠️ Could not connect to MCP server (this is expected if no server is running)")
            print("   This example demonstrates the protocol even without a live server")
        
        # Register custom tools
        print("\n🔧 Registering custom tools...")
        
        # Define a custom tool
        custom_tool = MCPTool(
            name="example_analysis",
            description="Perform example data analysis",
            input_schema={
                "type": "object",
                "properties": {
                    "data_source": {"type": "string", "description": "Data source to analyze"},
                    "analysis_type": {"type": "string", "description": "Type of analysis"}
                },
                "required": ["data_source"]
            }
        )
        
        async def example_analysis_handler(args):
            """Handler for example analysis tool."""
            data_source = args.get("data_source", "unknown")
            analysis_type = args.get("analysis_type", "basic")
            
            result = {
                "analysis_complete": True,
                "data_source": data_source,
                "analysis_type": analysis_type,
                "findings": [
                    "Data quality is good",
                    "No anomalies detected",
                    "Trends show positive growth"
                ]
            }
            
            return f"Analysis of {data_source} completed: {result}"
        
        await client.register_tool(custom_tool, example_analysis_handler)
        print(f"✅ Registered tool: {custom_tool.name}")
        
        # Try to register with server (will fail if no server)
        try:
            registration_ok = await client.register_with_server()
            if registration_ok:
                print("✅ Successfully registered agent with MCP server")
            else:
                print("⚠️ Could not register with MCP server")
        except Exception as e:
            print(f"⚠️ Registration failed (expected without server): {str(e)[:100]}...")
        
        # Demonstrate tool discovery
        try:
            print("\n📋 Discovering available tools...")
            tools = await client.list_tools()
            print(f"✅ Discovered {len(tools)} tools")
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")
        except Exception as e:
            print(f"⚠️ Tool discovery failed (expected without server): {str(e)[:100]}...")
        
        # Demonstrate A2A agent discovery
        try:
            print("\n🤖 Discovering other agents...")
            agents = await client.discover_agents()
            print(f"✅ Discovered {len(agents)} agents")
            for agent in agents:
                print(f"   - {agent.name} ({agent.id}): {', '.join(agent.capabilities)}")
        except Exception as e:
            print(f"⚠️ Agent discovery failed (expected without server): {str(e)[:100]}...")
    
    finally:
        await client.close()

async def demonstrate_a2a_communication():
    """Demonstrate Agent-to-Agent communication."""
    print("\n🤖 Agent-to-Agent Communication Demonstration")
    print("=" * 55)
    
    # Create two agents
    agent1 = MCPProtocolClient(
        server_url="http://localhost:5000",
        agent_name="DatabaseAgent",
        capabilities=["database_query", "data_retrieval"]
    )
    
    agent2 = MCPProtocolClient(
        server_url="http://localhost:5000", 
        agent_name="ReportingAgent",
        capabilities=["report_generation", "data_visualization"]
    )
    
    print(f"✅ Created Agent 1: {agent1.agent_name}")
    print(f"✅ Created Agent 2: {agent2.agent_name}")
    
    try:
        # Register custom tools for each agent
        
        # Agent 1 tools (Database Agent)
        db_tool = MCPTool(
            name="query_database",
            description="Query the database for information",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "SQL-like query"},
                    "table": {"type": "string", "description": "Table name"}
                },
                "required": ["query"]
            }
        )
        
        async def db_query_handler(args):
            query = args.get("query", "")
            table = args.get("table", "users")
            return f"Database query '{query}' on table '{table}' returned 42 records"
        
        await agent1.register_tool(db_tool, db_query_handler)
        
        # Agent 2 tools (Reporting Agent)
        report_tool = MCPTool(
            name="generate_report",
            description="Generate a data report",
            input_schema={
                "type": "object", 
                "properties": {
                    "data": {"type": "string", "description": "Data to include in report"},
                    "format": {"type": "string", "description": "Report format"}
                },
                "required": ["data"]
            }
        )
        
        async def report_handler(args):
            data = args.get("data", "")
            format_type = args.get("format", "summary")
            return f"Generated {format_type} report for data: {data}"
        
        await agent2.register_tool(report_tool, report_handler)
        
        print("✅ Registered tools for both agents")
        
        # Simulate A2A communication workflow
        print("\n📡 Simulating A2A communication workflow...")
        
        # Step 1: Agent 1 (Database) queries data
        print("   Step 1: Database Agent queries data")
        db_result = await db_query_handler({"query": "SELECT * FROM sales", "table": "sales"})
        print(f"     Result: {db_result}")
        
        # Step 2: Agent 1 sends data to Agent 2 for reporting
        print("   Step 2: Database Agent requests report from Reporting Agent")
        
        # In a real scenario, this would be an MCP call through the server
        # Here we simulate the communication
        try:
            # This would normally be: await agent1.call_agent(agent2.agent_id, "generate_report", {...})
            report_result = await report_handler({
                "data": db_result,
                "format": "executive_summary"
            })
            print(f"     Report: {report_result}")
            print("✅ A2A communication workflow completed successfully")
            
        except Exception as e:
            print(f"⚠️ A2A call failed (expected without server): {str(e)[:100]}...")
    
    finally:
        await agent1.close()
        await agent2.close()

async def demonstrate_database_agent_with_mcp():
    """Demonstrate DatabaseAgent using MCP protocol."""
    print("\n🗄️ Database Agent with MCP Protocol")
    print("=" * 45)
    
    # Create MCP client
    mcp_client = MCPProtocolClient(
        server_url="http://localhost:5000",
        agent_name="DatabaseAgent",
        capabilities=["database_query", "data_analysis", "reporting"]
    )
    
    try:
        # Create database agent using MCP protocol
        agent = DatabaseAgent(
            mcp_client=mcp_client,
            use_mcp_protocol=True,
            temperature=0.1
        )
        
        print("✅ Created Database Agent with MCP protocol support")
        print(f"   Agent uses MCP protocol: {agent.use_mcp_protocol}")
        print(f"   Tools loaded: {len(agent.tools)}")
        
        # Get tool information
        tools_info = agent.get_tool_info()
        print("\n📋 Available tools:")
        for tool in tools_info:
            print(f"   - {tool['name']}: {tool['description']}")
        
        # Test agent suggestions
        print("\n💡 Suggested queries:")
        suggestions = agent.suggest_queries("user data analysis")
        for i, suggestion in enumerate(suggestions, 1):
            print(f"   {i}. {suggestion}")
        
        print("\n✅ Database Agent MCP integration demonstration complete")
        
    except Exception as e:
        print(f"⚠️ Database Agent setup failed: {e}")
        logger.exception("Database Agent error")
    
    finally:
        await mcp_client.close()

async def main():
    """Main demonstration function."""
    print("🚀 MCP Protocol and A2A Communication Examples")
    print("=" * 60)
    print("\nThis example demonstrates:")
    print("• Real MCP protocol implementation")
    print("• Agent-to-Agent communication")
    print("• Tool registration and discovery")
    print("• Database Agent integration")
    print("• Protocol compliance testing")
    
    try:
        # Run demonstrations
        await demonstrate_mcp_protocol()
        await demonstrate_a2a_communication()
        await demonstrate_database_agent_with_mcp()
        
        print("\n🎉 All demonstrations completed successfully!")
        print("\nNext steps:")
        print("• Set up a real MCP server to test live communication")
        print("• Implement additional agent capabilities")
        print("• Create multi-agent workflows")
        print("• Add resource management and streaming support")
        
    except Exception as e:
        print(f"\n❌ Demonstration failed: {e}")
        logger.exception("Main demonstration error")

if __name__ == "__main__":
    asyncio.run(main())
