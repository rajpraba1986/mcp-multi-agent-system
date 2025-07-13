#!/usr/bin/env python3
"""
Simple Query Example for MCP Toolbox Integration with Anthropic Claude.

This example demonstrates basic usage of the MCP Toolbox client
to perform simple database queries through natural language using Claude.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client.mcp_client import MCPToolboxClient, SyncMCPToolboxClient
from agents.database_agent import DatabaseAgent
from utils.logging import setup_logging
from utils.config import ConfigManager


async def main():
    """Main example function."""
    # Setup logging
    setup_logging(level="INFO")
    
    print("🚀 MCP Toolbox Simple Query Example with Anthropic Claude")
    print("=" * 60)
    
    # Load configuration
    try:
        config_manager = ConfigManager()
        mcp_config = config_manager.get_mcp_config()
        llm_config = config_manager.get_llm_config()
        print(f"✅ Configuration loaded")
        print(f"   Server URL: {mcp_config.server_url}")
        print(f"   Tools file: {mcp_config.tools_file}")
        print(f"   LLM Provider: {llm_config.provider}")
        print(f"   LLM Model: {llm_config.model}")
    except Exception as e:
        print(f"⚠️  Configuration loading failed: {e}")
        print("   Using default configuration...")
        mcp_config = type('Config', (), {
            'server_url': 'http://localhost:5000',
            'tools_file': 'config/tools.yaml'
        })()
    
    # Initialize MCP client
    print(f"\n🔗 Connecting to MCP Toolbox server...")
    
    async with MCPToolboxClient(mcp_config.server_url) as client:
        # Test connection
        if await client.test_connection():
            print("✅ Successfully connected to MCP Toolbox server")
        else:
            print("❌ Failed to connect to MCP Toolbox server")
            print("   Make sure the MCP Toolbox server is running:")
            print(f"   ./toolbox --tools-file {mcp_config.tools_file}")
            return
        
        # Initialize database agent
        print("\n🤖 Initializing Database Agent...")
        agent = DatabaseAgent(client, toolset_name="user-management")
        
        # Get available tools info
        tools_info = agent.get_tool_info()
        print(f"✅ Agent initialized with {len(tools_info)} tools:")
        for tool in tools_info:
            print(f"   - {tool['name']}: {tool['description']}")
        
        # Example queries
        example_queries = [
            "Search for users with the name 'John'",
            "Find users who registered recently",
            "Show me user activity for user ID 1 in the last 7 days",
        ]
        
        print(f"\n📝 Running example queries...")
        print("-" * 40)
        
        for i, query in enumerate(example_queries, 1):
            print(f"\n🔍 Query {i}: {query}")
            print("💭 Processing...")
            
            try:
                result = agent.query(query)
                
                if result["success"]:
                    print("✅ Query completed successfully!")
                    print(f"📊 Answer: {result['answer']}")
                    
                    if result.get("intermediate_steps"):
                        print(f"🔧 Steps taken: {len(result['intermediate_steps'])}")
                else:
                    print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"💥 Error executing query: {e}")
            
            print("-" * 40)
        
        # Interactive mode
        print(f"\n🎯 Interactive Query Mode")
        print("Type your questions or 'quit' to exit")
        print("-" * 40)
        
        while True:
            try:
                user_query = input("\n🤔 Your question: ").strip()
                
                if user_query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if not user_query:
                    continue
                
                print("💭 Processing...")
                result = agent.query(user_query)
                
                if result["success"]:
                    print(f"🎯 Answer: {result['answer']}")
                else:
                    print(f"❌ Error: {result.get('error', 'Unknown error')}")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"💥 Error: {e}")
        
        print("\n👋 Thank you for using MCP Toolbox!")


def sync_example():
    """Synchronous version of the example."""
    print("🚀 MCP Toolbox Simple Query Example (Sync Version)")
    print("=" * 55)
    
    # Setup logging
    setup_logging(level="INFO")
    
    try:
        # Initialize sync client
        with SyncMCPToolboxClient("http://localhost:5000") as client:
            # Test connection
            if client.test_connection():
                print("✅ Successfully connected to MCP Toolbox server")
            else:
                print("❌ Failed to connect to MCP Toolbox server")
                return
            
            # Load tools
            tools = client.load_langchain_tools("user-management")
            print(f"✅ Loaded {len(tools)} tools")
            
            # Example direct tool execution
            print("\n🔧 Direct tool execution example:")
            try:
                result = client.execute_tool(
                    tool_name="search-users-by-name",
                    parameters={"name": "John"},
                    toolset_name="user-management"
                )
                print(f"📊 Direct tool result: {result}")
            except Exception as e:
                print(f"💥 Direct tool execution failed: {e}")
            
    except Exception as e:
        print(f"💥 Example failed: {e}")


if __name__ == "__main__":
    print("Choose example mode:")
    print("1. Async mode (recommended)")
    print("2. Sync mode")
    print("3. Both")
    
    choice = input("Enter your choice (1-3): ").strip()
    
    if choice == "1":
        asyncio.run(main())
    elif choice == "2":
        sync_example()
    elif choice == "3":
        print("\n" + "="*60)
        print("ASYNC MODE")
        print("="*60)
        asyncio.run(main())
        
        print("\n" + "="*60)
        print("SYNC MODE")
        print("="*60)
        sync_example()
    else:
        print("Invalid choice, running async mode...")
        asyncio.run(main())
