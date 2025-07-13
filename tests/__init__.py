"""
Test suite for MCP Toolbox integration.
"""

import pytest
import asyncio
from pathlib import Path
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Test configuration
TEST_CONFIG = {
    "mcp_server_url": "http://localhost:5000",
    "test_toolset": "user-management",
    "timeout": 30
}


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mcp_client():
    """Fixture to provide MCP client for tests."""
    from client.mcp_client import MCPToolboxClient
    
    client = MCPToolboxClient(TEST_CONFIG["mcp_server_url"])
    yield client
    await client.close()


@pytest.fixture
def sample_data():
    """Fixture providing sample test data."""
    return {
        "test_users": [
            {"name": "John Doe", "email": "john.doe@test.com"},
            {"name": "Jane Smith", "email": "jane.smith@test.com"}
        ],
        "test_queries": [
            "Find users with name John",
            "Search for recent user activity",
            "Get user statistics"
        ]
    }
