"""
Agents module for MCP Toolbox integration with LangGraph.
"""

# Import active agents
from .postgresql_database_agent import PostgreSQLDatabaseAgent

# Legacy imports (deprecated - use new agents above)
from .legacy_database_agent import DatabaseAgent
from .legacy_workflow import DatabaseWorkflow, AnalyticsWorkflow

__all__ = [
    # Active agents
    "PostgreSQLDatabaseAgent",
    # Legacy agents (deprecated)
    "DatabaseAgent",
    "DatabaseWorkflow",
    "AnalyticsWorkflow",
]
