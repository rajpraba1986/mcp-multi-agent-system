"""
Test Suite for MCP Toolbox Integration - Core Client Tests

Tests for the core MCP Toolbox client functionality including
connection handling, tool loading, and basic operations.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
from pathlib import Path

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from client.mcp_client import MCPToolboxClient, SyncMCPToolboxClient


class TestMCPToolboxClient:
    """Test cases for MCPToolboxClient."""
    
    @pytest.fixture
    def mock_toolbox_client(self):
        """Mock toolbox client for testing."""
        mock_client = Mock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock() 
        mock_client.load_toolset = AsyncMock(return_value=[])
        return mock_client
    
    @pytest.fixture
    def client(self):
        """Create client instance for testing."""
        return MCPToolboxClient("http://localhost:5000")
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.server_url == "http://localhost:5000"
        assert client.timeout == 30.0
        assert client._client is None
        assert not client._connected
    
    @pytest.mark.asyncio
    async def test_connection_success(self, client, mock_toolbox_client):
        """Test successful connection."""
        with patch('toolbox_core.ToolboxClient', return_value=mock_toolbox_client):
            await client.connect()
            assert client._connected
            mock_toolbox_client.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connection_failure(self, client):
        """Test connection failure handling."""
        with patch('toolbox_core.ToolboxClient', side_effect=Exception("Connection failed")):
            with pytest.raises(Exception, match="Connection failed"):
                await client.connect()
            assert not client._connected
    
    @pytest.mark.asyncio
    async def test_test_connection_success(self, client, mock_toolbox_client):
        """Test connection testing."""
        with patch('toolbox_core.ToolboxClient', return_value=mock_toolbox_client):
            result = await client.test_connection()
            assert result is True
    
    @pytest.mark.asyncio
    async def test_test_connection_failure(self, client):
        """Test connection testing failure."""
        with patch('toolbox_core.ToolboxClient', side_effect=Exception("Failed")):
            result = await client.test_connection()
            assert result is False
    
    @pytest.mark.asyncio
    async def test_load_toolset_success(self, client, mock_toolbox_client):
        """Test successful toolset loading."""
        mock_tools = [Mock(name="tool1"), Mock(name="tool2")]
        mock_toolbox_client.load_toolset.return_value = mock_tools
        
        with patch('toolbox_core.ToolboxClient', return_value=mock_toolbox_client):
            await client.connect()
            tools = await client.load_toolset("test-toolset")
            
            assert len(tools) == 2
            mock_toolbox_client.load_toolset.assert_called_with("test-toolset")
    
    @pytest.mark.asyncio
    async def test_load_toolset_not_connected(self, client):
        """Test toolset loading when not connected."""
        with pytest.raises(RuntimeError, match="Client not connected"):
            await client.load_toolset("test-toolset")
    
    @pytest.mark.asyncio
    async def test_context_manager(self, client, mock_toolbox_client):
        """Test async context manager functionality."""
        with patch('toolbox_core.ToolboxClient', return_value=mock_toolbox_client):
            async with client:
                assert client._connected
            
            mock_toolbox_client.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, client, mock_toolbox_client):
        """Test client cleanup."""
        with patch('toolbox_core.ToolboxClient', return_value=mock_toolbox_client):
            await client.connect()
            await client.close()
            
            assert not client._connected
            mock_toolbox_client.disconnect.assert_called_once()


class TestSyncMCPToolboxClient:
    """Test cases for SyncMCPToolboxClient."""
    
    @pytest.fixture
    def sync_client(self):
        """Create sync client instance for testing."""
        return SyncMCPToolboxClient("http://localhost:5000")
    
    def test_sync_client_initialization(self, sync_client):
        """Test sync client initialization."""
        assert sync_client.server_url == "http://localhost:5000"
        assert sync_client._async_client is not None
    
    def test_test_connection_sync(self, sync_client):
        """Test sync connection testing."""
        with patch.object(sync_client._async_client, 'test_connection', 
                         AsyncMock(return_value=True)):
            result = sync_client.test_connection()
            assert result is True
    
    def test_load_toolset_sync(self, sync_client):
        """Test sync toolset loading."""
        mock_tools = [Mock(name="tool1"), Mock(name="tool2")]
        
        with patch.object(sync_client._async_client, 'load_toolset',
                         AsyncMock(return_value=mock_tools)):
            tools = sync_client.load_toolset("test-toolset")
            assert len(tools) == 2
    
    def test_context_manager_sync(self, sync_client):
        """Test sync context manager."""
        with patch.object(sync_client._async_client, 'connect', AsyncMock()):
            with patch.object(sync_client._async_client, 'close', AsyncMock()):
                with sync_client:
                    pass  # Context manager should work


@pytest.mark.integration
class TestMCPToolboxClientIntegration:
    """Integration tests for MCP Toolbox client."""
    
    @pytest.mark.asyncio
    async def test_real_connection(self):
        """Test connection to real MCP server (if available)."""
        client = MCPToolboxClient("http://localhost:5000")
        
        try:
            # Try to connect - this may fail if server is not running
            connected = await client.test_connection()
            
            if connected:
                # If connection successful, test basic operations
                await client.connect()
                tools = await client.load_toolset()
                assert isinstance(tools, list)
                await client.close()
            else:
                # Server not available - skip test
                pytest.skip("MCP Toolbox server not available")
                
        except Exception as e:
            pytest.skip(f"MCP Toolbox server not available: {e}")
    
    @pytest.mark.asyncio
    async def test_multiple_clients(self):
        """Test multiple client instances."""
        clients = [
            MCPToolboxClient("http://localhost:5000"),
            MCPToolboxClient("http://localhost:5000")
        ]
        
        # Test that multiple clients can be created
        for client in clients:
            assert client.server_url == "http://localhost:5000"
        
        # Clean up
        for client in clients:
            await client.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
