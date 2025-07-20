#!/usr/bin/env python3
"""
Interactive Chat Interface for MCP Toolbox Integration with Anthropic Claude.

This example provides a rich interactive chat interface for users
to interact with their database through natural language queries using Claude.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client.mcp_client import MCPToolboxClient
from agents.legacy_database_agent import DatabaseAgent
from agents.workflow import InteractiveWorkflow
from utils.logging import setup_logging
from utils.config import ConfigManager


class ChatInterface:
    """Interactive chat interface for MCP Toolbox with Anthropic Claude."""
    
    def __init__(self, client: MCPToolboxClient):
        """Initialize the chat interface."""
        self.client = client
        self.agent = DatabaseAgent(client, toolset_name="all-tools")
        self.interactive_workflow = InteractiveWorkflow(client)
        self.conversation_history = []
        self.session_start = datetime.now()
        
    def print_welcome(self):
        """Print welcome message."""
        print("🤖 MCP Toolbox Interactive Chat Interface")
        print("=" * 50)
        print("Welcome! I'm your intelligent database assistant.")
        print("I can help you query, analyze, and understand your data.")
        print("\nWhat I can do:")
        print("• Answer questions about your data")
        print("• Perform complex analytics")
        print("• Generate reports and summaries")
        print("• Search and filter information")
        print("• Provide insights and recommendations")
        print("\nCommands:")
        print("• 'help' - Show available commands")
        print("• 'tools' - List available database tools")
        print("• 'suggestions' - Get query suggestions")
        print("• 'summary' - Get conversation summary")
        print("• 'export' - Export conversation")
        print("• 'clear' - Clear conversation history")
        print("• 'quit' or 'exit' - End session")
        print("-" * 50)
        
    def print_tools_info(self):
        """Print information about available tools."""
        print("\n🔧 Available Database Tools:")
        print("-" * 30)
        
        tools_info = self.agent.get_tool_info()
        for i, tool in enumerate(tools_info, 1):
            print(f"{i}. {tool['name']}")
            print(f"   📝 {tool['description']}")
            print(f"   🏷️  Type: {tool['type']}")
            print()
    
    def print_suggestions(self):
        """Print query suggestions."""
        print("\n💡 Query Suggestions:")
        print("-" * 25)
        
        suggestions = self.agent.suggest_queries()
        for i, suggestion in enumerate(suggestions, 1):
            print(f"{i}. {suggestion}")
        print()
    
    def print_conversation_summary(self):
        """Print conversation summary."""
        print("\n📋 Conversation Summary:")
        print("-" * 25)
        
        if not self.conversation_history:
            print("No conversation history yet.")
            return
        
        summary = self.interactive_workflow.get_conversation_summary()
        print(summary)
        print(f"\nSession info:")
        print(f"• Started: {self.session_start.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"• Duration: {datetime.now() - self.session_start}")
        print(f"• Exchanges: {len(self.conversation_history) // 2}")
    
    def export_conversation(self):
        """Export conversation to file."""
        if not self.conversation_history:
            print("❌ No conversation to export.")
            return
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_export_{timestamp}.json"
        
        export_data = {
            "session_start": self.session_start.isoformat(),
            "session_end": datetime.now().isoformat(),
            "conversation_history": self.conversation_history,
            "total_exchanges": len(self.conversation_history) // 2
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(export_data, f, indent=2, default=str)
            print(f"✅ Conversation exported to: {filename}")
        except Exception as e:
            print(f"❌ Export failed: {e}")
    
    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history.clear()
        self.interactive_workflow.clear_conversation()
        print("✅ Conversation history cleared.")
    
    def process_query(self, query: str) -> dict:
        """Process a user query and return results."""
        print("💭 Processing your query...")
        
        try:
            # Use interactive workflow for better context
            result = self.interactive_workflow.continue_conversation(query)
            
            # Store in our history for export
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "user",
                "content": query
            })
            
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "assistant",
                "content": result["response"],
                "success": result["success"]
            })
            
            return result
            
        except Exception as e:
            error_result = {
                "response": f"I encountered an error: {e}",
                "success": False,
                "error": str(e)
            }
            
            self.conversation_history.append({
                "timestamp": datetime.now().isoformat(),
                "type": "assistant",
                "content": error_result["response"],
                "success": False,
                "error": str(e)
            })
            
            return error_result
    
    def format_response(self, result: dict):
        """Format and display the assistant's response."""
        if result["success"]:
            print("🎯 Answer:")
            print(f"   {result['response']}")
            
            # Show suggestions if available
            if result.get("suggestions"):
                print(f"\n💡 You might also ask:")
                for suggestion in result["suggestions"][:3]:
                    print(f"   • {suggestion}")
        else:
            print("❌ I encountered an issue:")
            print(f"   {result['response']}")
            if result.get("error"):
                print(f"   Error details: {result['error']}")
    
    async def run(self):
        """Run the interactive chat interface."""
        self.print_welcome()
        
        # Test connection
        if not await self.client.test_connection():
            print("❌ Cannot connect to MCP Toolbox server")
            print("Make sure the server is running with: ./toolbox --tools-file config/tools.yaml")
            return
        
        print("✅ Connected to MCP Toolbox server")
        print("\n🎬 Chat session started! Type your question or 'help' for commands.")
        
        while True:
            try:
                # Get user input
                print("\n" + "-" * 50)
                user_input = input("🤔 You: ").strip()
                
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("\n👋 Thank you for using MCP Toolbox Chat!")
                    print("Have a great day! 🌟")
                    break
                
                elif user_input.lower() == 'help':
                    self.print_welcome()
                    continue
                
                elif user_input.lower() == 'tools':
                    self.print_tools_info()
                    continue
                
                elif user_input.lower() == 'suggestions':
                    self.print_suggestions()
                    continue
                
                elif user_input.lower() == 'summary':
                    self.print_conversation_summary()
                    continue
                
                elif user_input.lower() == 'export':
                    self.export_conversation()
                    continue
                
                elif user_input.lower() == 'clear':
                    self.clear_conversation()
                    continue
                
                # Process regular query
                result = self.process_query(user_input)
                self.format_response(result)
                
            except KeyboardInterrupt:
                print("\n\n⚠️  Session interrupted by user")
                break
            except EOFError:
                print("\n\n👋 Session ended")
                break
            except Exception as e:
                print(f"\n💥 Unexpected error: {e}")
                print("The chat will continue...")


class EnhancedChatInterface(ChatInterface):
    """Enhanced chat interface with additional features."""
    
    def __init__(self, client: MCPToolboxClient):
        super().__init__(client)
        self.favorites = []
        self.query_stats = {"total": 0, "successful": 0, "failed": 0}
    
    def add_to_favorites(self, query: str):
        """Add a query to favorites."""
        if query not in self.favorites:
            self.favorites.append(query)
            print(f"⭐ Added to favorites: {query}")
        else:
            print("⭐ Already in favorites!")
    
    def show_favorites(self):
        """Show favorite queries."""
        if not self.favorites:
            print("⭐ No favorite queries yet.")
            return
        
        print("\n⭐ Favorite Queries:")
        for i, fav in enumerate(self.favorites, 1):
            print(f"{i}. {fav}")
    
    def show_stats(self):
        """Show session statistics."""
        print(f"\n📊 Session Statistics:")
        print(f"• Total queries: {self.query_stats['total']}")
        print(f"• Successful: {self.query_stats['successful']}")
        print(f"• Failed: {self.query_stats['failed']}")
        if self.query_stats['total'] > 0:
            success_rate = (self.query_stats['successful'] / self.query_stats['total']) * 100
            print(f"• Success rate: {success_rate:.1f}%")
    
    def process_query(self, query: str) -> dict:
        """Enhanced query processing with statistics."""
        self.query_stats['total'] += 1
        result = super().process_query(query)
        
        if result['success']:
            self.query_stats['successful'] += 1
        else:
            self.query_stats['failed'] += 1
        
        return result
    
    async def run(self):
        """Enhanced run method with additional commands."""
        print("🚀 Enhanced MCP Toolbox Chat Interface")
        print("Additional commands:")
        print("• 'favorites' - Show favorite queries")
        print("• 'fav <query>' - Add query to favorites")
        print("• 'stats' - Show session statistics")
        print("-" * 50)
        
        await super().run()


async def main():
    """Main function to run the chat interface."""
    # Setup logging
    setup_logging(level="WARNING")  # Reduce noise for chat
    
    # Load configuration
    try:
        config_manager = ConfigManager()
        mcp_config = config_manager.get_mcp_config()
    except Exception:
        # Use defaults if config loading fails
        mcp_config = type('Config', (), {'server_url': 'http://localhost:5000'})()
    
    # Initialize client and chat interface
    async with MCPToolboxClient(mcp_config.server_url) as client:
        # Choose interface type
        print("Choose chat interface:")
        print("1. Standard Chat Interface")
        print("2. Enhanced Chat Interface (with favorites & stats)")
        
        choice = input("Enter your choice (1-2): ").strip()
        
        if choice == "2":
            chat = EnhancedChatInterface(client)
        else:
            chat = ChatInterface(client)
        
        await chat.run()


if __name__ == "__main__":
    asyncio.run(main())
