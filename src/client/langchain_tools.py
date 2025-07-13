"""
LangChain Tools Integration for MCP Toolbox.

This module provides LangChain-specific implementations and utilities
for working with MCP Toolbox tools in the LangChain ecosystem.
"""

import logging
from typing import Dict, List, Optional, Any, Type, Callable
from abc import ABC, abstractmethod

from langchain_core.tools import BaseTool
from langchain_core.callbacks import CallbackManagerForToolRun
from pydantic import BaseModel, Field

from .mcp_client import MCPToolboxClient


logger = logging.getLogger(__name__)


class MCPToolSchema(BaseModel):
    """Schema for MCP tool parameters."""
    pass


class MCPBaseTool(BaseTool, ABC):
    """
    Base class for MCP Toolbox tools integrated with LangChain.
    
    This class wraps MCP Toolbox tools to make them compatible with
    the LangChain BaseTool interface.
    """
    
    mcp_client: MCPToolboxClient = Field(exclude=True)
    tool_name: str = Field(description="Name of the MCP tool")
    toolset_name: Optional[str] = Field(default=None, description="Toolset containing this tool")
    
    class Config:
        arbitrary_types_allowed = True
    
    def __init__(self, mcp_client: MCPToolboxClient, tool_name: str, **data):
        super().__init__(mcp_client=mcp_client, tool_name=tool_name, **data)
    
    @abstractmethod
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the tool."""
        pass
    
    async def _arun(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the tool asynchronously."""
        try:
            result = await self.mcp_client.execute_tool(
                tool_name=self.tool_name,
                parameters=kwargs,
                toolset_name=self.toolset_name
            )
            return result
        except Exception as e:
            logger.error(f"Error executing MCP tool '{self.tool_name}': {e}")
            raise


class MCPSQLTool(MCPBaseTool):
    """
    LangChain tool for SQL-based MCP Toolbox tools.
    """
    
    name: str = "mcp_sql_tool"
    description: str = "Execute SQL queries through MCP Toolbox"
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the SQL tool synchronously."""
        import asyncio
        return asyncio.run(self._arun(run_manager, **kwargs))


class MCPSearchTool(MCPBaseTool):
    """
    LangChain tool for search-based MCP Toolbox tools.
    """
    
    name: str = "mcp_search_tool"
    description: str = "Search data through MCP Toolbox"
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the search tool synchronously."""
        import asyncio
        return asyncio.run(self._arun(run_manager, **kwargs))


class MCPAnalyticsTool(MCPBaseTool):
    """
    LangChain tool for analytics-based MCP Toolbox tools.
    """
    
    name: str = "mcp_analytics_tool"
    description: str = "Perform analytics through MCP Toolbox"
    
    def _run(
        self,
        run_manager: Optional[CallbackManagerForToolRun] = None,
        **kwargs: Any,
    ) -> Any:
        """Execute the analytics tool synchronously."""
        import asyncio
        return asyncio.run(self._arun(run_manager, **kwargs))


class MCPLangChainTools:
    """
    Factory class for creating LangChain-compatible tools from MCP Toolbox.
    
    This class provides utilities to convert MCP Toolbox tools into
    LangChain BaseTool instances for easy integration with LangChain agents.
    """
    
    def __init__(self, mcp_client: MCPToolboxClient):
        """
        Initialize the LangChain tools factory.
        
        Args:
            mcp_client: MCP Toolbox client instance
        """
        self.mcp_client = mcp_client
        self._tool_mapping = {
            'sql': MCPSQLTool,
            'search': MCPSearchTool,
            'analytics': MCPAnalyticsTool,
        }
        
        logger.info("Initialized MCP LangChain tools factory")
    
    def create_tool_from_definition(
        self,
        tool_definition: Dict[str, Any],
        toolset_name: Optional[str] = None
    ) -> BaseTool:
        """
        Create a LangChain tool from an MCP tool definition.
        
        Args:
            tool_definition: MCP tool definition dictionary
            toolset_name: Optional toolset name
            
        Returns:
            BaseTool: LangChain-compatible tool
        """
        tool_name = tool_definition.get('name', 'unknown_tool')
        tool_description = tool_definition.get('description', f"MCP tool: {tool_name}")
        tool_kind = tool_definition.get('kind', 'sql')
        
        # Determine the appropriate tool class based on the tool kind
        tool_class = self._get_tool_class(tool_kind)
        
        # Create the tool instance
        tool = tool_class(
            mcp_client=self.mcp_client,
            tool_name=tool_name,
            toolset_name=toolset_name,
            name=tool_name,
            description=tool_description
        )
        
        logger.info(f"Created LangChain tool '{tool_name}' of type {tool_class.__name__}")
        return tool
    
    def _get_tool_class(self, tool_kind: str) -> Type[MCPBaseTool]:
        """
        Get the appropriate tool class based on the tool kind.
        
        Args:
            tool_kind: Kind of MCP tool (e.g., 'postgres-sql', 'search', etc.)
            
        Returns:
            Type[MCPBaseTool]: Appropriate tool class
        """
        # Map tool kinds to tool classes
        if 'sql' in tool_kind.lower():
            return MCPSQLTool
        elif 'search' in tool_kind.lower():
            return MCPSearchTool
        elif 'analytics' in tool_kind.lower():
            return MCPAnalyticsTool
        else:
            # Default to SQL tool for unknown types
            return MCPSQLTool
    
    async def create_tools_from_toolset(
        self,
        toolset_name: Optional[str] = None
    ) -> List[BaseTool]:
        """
        Create LangChain tools from an MCP toolset.
        
        Args:
            toolset_name: Name of the toolset to load
            
        Returns:
            List[BaseTool]: List of LangChain-compatible tools
        """
        try:
            # Load tools using the LangChain client
            langchain_tools = await self.mcp_client.load_langchain_tools(toolset_name)
            
            # If the MCP client returns LangChain tools directly, use them
            if langchain_tools and all(isinstance(tool, BaseTool) for tool in langchain_tools):
                logger.info(f"Loaded {len(langchain_tools)} LangChain tools from MCP Toolbox")
                return langchain_tools
            
            # Otherwise, create tools from definitions
            tools = []
            core_tools = await self.mcp_client.load_toolset(toolset_name)
            
            for tool_def in core_tools:
                if isinstance(tool_def, dict):
                    tool = self.create_tool_from_definition(tool_def, toolset_name)
                    tools.append(tool)
                else:
                    # If it's already a tool object, try to wrap it
                    wrapped_tool = self._wrap_tool_object(tool_def, toolset_name)
                    if wrapped_tool:
                        tools.append(wrapped_tool)
            
            logger.info(f"Created {len(tools)} LangChain tools from toolset '{toolset_name}'")
            return tools
            
        except Exception as e:
            logger.error(f"Failed to create tools from toolset '{toolset_name}': {e}")
            raise
    
    def _wrap_tool_object(
        self,
        tool_obj: Any,
        toolset_name: Optional[str] = None
    ) -> Optional[BaseTool]:
        """
        Wrap a tool object into a LangChain tool.
        
        Args:
            tool_obj: Tool object from MCP Toolbox
            toolset_name: Optional toolset name
            
        Returns:
            Optional[BaseTool]: Wrapped tool or None if wrapping failed
        """
        try:
            # Extract tool information
            tool_name = getattr(tool_obj, 'name', 'wrapped_tool')
            tool_description = getattr(tool_obj, 'description', f"Wrapped MCP tool: {tool_name}")
            
            class WrappedMCPTool(MCPBaseTool):
                name = tool_name
                description = tool_description
                
                def _run(self, run_manager=None, **kwargs):
                    # Call the original tool
                    if callable(tool_obj):
                        return tool_obj(**kwargs)
                    else:
                        raise ValueError(f"Tool object {tool_name} is not callable")
            
            return WrappedMCPTool(
                mcp_client=self.mcp_client,
                tool_name=tool_name,
                toolset_name=toolset_name
            )
            
        except Exception as e:
            logger.warning(f"Failed to wrap tool object: {e}")
            return None
    
    def create_custom_tool(
        self,
        name: str,
        description: str,
        func: Callable,
        toolset_name: Optional[str] = None
    ) -> BaseTool:
        """
        Create a custom LangChain tool with a provided function.
        
        Args:
            name: Tool name
            description: Tool description
            func: Function to execute
            toolset_name: Optional toolset name
            
        Returns:
            BaseTool: Custom LangChain tool
        """
        class CustomMCPTool(MCPBaseTool):
            def _run(self, run_manager=None, **kwargs):
                return func(**kwargs)
        
        tool = CustomMCPTool(
            mcp_client=self.mcp_client,
            tool_name=name,
            toolset_name=toolset_name,
            name=name,
            description=description
        )
        
        logger.info(f"Created custom tool '{name}'")
        return tool


def create_langchain_tools_sync(
    mcp_client: MCPToolboxClient,
    toolset_name: Optional[str] = None
) -> List[BaseTool]:
    """
    Synchronous helper function to create LangChain tools.
    
    Args:
        mcp_client: MCP Toolbox client
        toolset_name: Optional toolset name
        
    Returns:
        List[BaseTool]: List of LangChain tools
    """
    import asyncio
    
    factory = MCPLangChainTools(mcp_client)
    return asyncio.run(factory.create_tools_from_toolset(toolset_name))
