"""
MCP Toolbox Integration with LangChain and LangGraph

This package provides a comprehensive implementation for integrating Google's MCP Toolbox
with LangChain and LangGraph frameworks to build powerful AI agents with database access.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .client.mcp_client import MCPToolboxClient
# Import active PostgreSQL agent
from .agents.postgresql_database_agent import PostgreSQLDatabaseAgent
# Legacy import (deprecated)
from .agents.legacy_database_agent import DatabaseAgent

__all__ = [
    "MCPToolboxClient",
    "PostgreSQLDatabaseAgent",  # Active agent
    "DatabaseAgent",  # Legacy agent (deprecated)
]
