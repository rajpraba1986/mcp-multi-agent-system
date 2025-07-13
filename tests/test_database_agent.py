"""
Test Suite for Database Agent - MCP Toolbox Integration

Tests for the database agent functionality including
query processing, error handling, and tool integration.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from agents.database_agent import DatabaseAgent


class TestDatabaseAgent:
    """Test cases for DatabaseAgent."""
    
    @pytest.fixture
    def mock_mcp_client(self):
        """Mock MCP client for testing."""
        mock_client = Mock()
        mock_client.load_toolset = AsyncMock(return_value=[])
        mock_client.close = AsyncMock()
        return mock_client
    
    @pytest.fixture
    def mock_tools(self):
        """Mock tools for testing."""
        tool1 = Mock()
        tool1.name = "query_database"
        tool1.description = "Execute database queries"
        tool1.invoke = AsyncMock(return_value="Query result")
        
        tool2 = Mock()
        tool2.name = "analyze_data"
        tool2.description = "Analyze data patterns"
        tool2.invoke = AsyncMock(return_value="Analysis result")
        
        return [tool1, tool2]
    
    @pytest.fixture
    def agent(self, mock_mcp_client):
        """Create agent instance for testing."""
        return DatabaseAgent(mock_mcp_client, temperature=0.1)
    
    @pytest.mark.asyncio
    async def test_agent_initialization(self, agent, mock_mcp_client):
        """Test agent initialization."""
        assert agent.mcp_client == mock_mcp_client
        assert agent.temperature == 0.1
        assert agent.toolset_name == "all-tools"
        assert agent._tools is None
    
    @pytest.mark.asyncio
    async def test_load_tools_success(self, agent, mock_mcp_client, mock_tools):
        """Test successful tool loading."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        
        await agent._load_tools()
        
        assert agent._tools == mock_tools
        assert len(agent._tools) == 2
        mock_mcp_client.load_toolset.assert_called_once_with("all-tools")
    
    @pytest.mark.asyncio
    async def test_load_tools_failure(self, agent, mock_mcp_client):
        """Test tool loading failure."""
        mock_mcp_client.load_toolset.side_effect = Exception("Load failed")
        
        with pytest.raises(Exception, match="Load failed"):
            await agent._load_tools()
    
    @pytest.mark.asyncio
    async def test_query_success(self, agent, mock_mcp_client, mock_tools):
        """Test successful query execution."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        
        # Mock LangChain components
        with patch('langchain_core.tools.BaseTool'):
            with patch('langchain_openai.ChatOpenAI') as mock_llm:
                mock_llm.return_value.invoke.return_value.content = "Query result"
                
                result = await agent.query("What is the total sales?")
                
                assert "Query result" in str(result)
    
    @pytest.mark.asyncio
    async def test_query_empty_input(self, agent):
        """Test query with empty input."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await agent.query("")
    
    @pytest.mark.asyncio
    async def test_query_none_input(self, agent):
        """Test query with None input."""
        with pytest.raises(ValueError, match="Query cannot be empty"):
            await agent.query(None)
    
    @pytest.mark.asyncio
    async def test_get_tool_info(self, agent, mock_mcp_client, mock_tools):
        """Test getting tool information."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        await agent._load_tools()
        
        tool_info = agent.get_tool_info()
        
        assert len(tool_info) == 2
        assert tool_info[0]["name"] == "query_database"
        assert tool_info[0]["description"] == "Execute database queries"
        assert tool_info[1]["name"] == "analyze_data"
        assert tool_info[1]["description"] == "Analyze data patterns"
    
    @pytest.mark.asyncio
    async def test_get_tool_info_no_tools(self, agent):
        """Test getting tool info when no tools loaded."""
        tool_info = agent.get_tool_info()
        assert tool_info == []
    
    @pytest.mark.asyncio
    async def test_analytics_query(self, agent, mock_mcp_client, mock_tools):
        """Test analytics-focused query."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        
        with patch('langchain_core.tools.BaseTool'):
            with patch('langchain_openai.ChatOpenAI') as mock_llm:
                mock_llm.return_value.invoke.return_value.content = "Analytics result"
                
                result = await agent.analytics_query(
                    "Analyze customer behavior patterns",
                    analysis_type="behavior_analysis"
                )
                
                assert "Analytics result" in str(result)
    
    @pytest.mark.asyncio
    async def test_context_manager(self, agent, mock_mcp_client):
        """Test agent as context manager."""
        async with agent:
            pass
        
        mock_mcp_client.close.assert_called_once()


@pytest.mark.integration
class TestDatabaseAgentIntegration:
    """Integration tests for DatabaseAgent."""
    
    @pytest.mark.asyncio
    async def test_agent_with_real_client(self):
        """Test agent with real MCP client (if available)."""
        from client.mcp_client import MCPToolboxClient
        
        client = MCPToolboxClient("http://localhost:5000")
        
        try:
            connected = await client.test_connection()
            
            if connected:
                agent = DatabaseAgent(client, temperature=0.1)
                
                # Test basic functionality
                tool_info = agent.get_tool_info()
                assert isinstance(tool_info, list)
                
                await client.close()
            else:
                pytest.skip("MCP Toolbox server not available")
                
        except Exception as e:
            pytest.skip(f"MCP Toolbox server not available: {e}")
    
    @pytest.mark.asyncio
    async def test_query_with_real_tools(self):
        """Test query execution with real tools (if available)."""
        from client.mcp_client import MCPToolboxClient
        
        client = MCPToolboxClient("http://localhost:5000")
        
        try:
            connected = await client.test_connection()
            
            if connected:
                agent = DatabaseAgent(client, temperature=0.1)
                
                # Test with a simple query
                result = await agent.query("Show database schema")
                assert result is not None
                
                await client.close()
            else:
                pytest.skip("MCP Toolbox server not available")
                
        except Exception as e:
            pytest.skip(f"MCP Toolbox server not available: {e}")


class TestDatabaseAgentEdgeCases:
    """Test edge cases for DatabaseAgent."""
    
    @pytest.fixture
    def agent_with_no_tools(self, mock_mcp_client):
        """Agent with no tools available."""
        mock_mcp_client.load_toolset.return_value = []
        return DatabaseAgent(mock_mcp_client)
    
    @pytest.mark.asyncio
    async def test_query_with_no_tools(self, agent_with_no_tools):
        """Test query when no tools are available."""
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_llm.return_value.invoke.return_value.content = "No tools available"
            
            result = await agent_with_no_tools.query("Test query")
            assert "No tools available" in str(result)
    
    @pytest.mark.asyncio
    async def test_very_long_query(self, agent, mock_mcp_client, mock_tools):
        """Test with very long query."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        
        long_query = "SELECT * FROM table WHERE " + "condition AND " * 1000 + "final_condition"
        
        with patch('langchain_core.tools.BaseTool'):
            with patch('langchain_openai.ChatOpenAI') as mock_llm:
                mock_llm.return_value.invoke.return_value.content = "Long query processed"
                
                result = await agent.query(long_query)
                assert result is not None
    
    @pytest.mark.asyncio
    async def test_special_characters_query(self, agent, mock_mcp_client, mock_tools):
        """Test query with special characters."""
        mock_mcp_client.load_toolset.return_value = mock_tools
        
        special_query = "Find records with 'special' characters: ñáéíóú & symbols!"
        
        with patch('langchain_core.tools.BaseTool'):
            with patch('langchain_openai.ChatOpenAI') as mock_llm:
                mock_llm.return_value.invoke.return_value.content = "Special chars handled"
                
                result = await agent.query(special_query)
                assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
