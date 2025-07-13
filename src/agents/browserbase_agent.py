"""
Browserbase Web Agent for MCP Toolbox Integration.

This agent integrates with the Browserbase MCP server to perform web automation,
data extraction, and browser interactions. It can extract information from websites
and store it in SQLite database.
"""

import asyncio
import json
import logging
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.language_models import BaseLanguageModel

from ..client.mcp_client import MCPToolboxClient
from ..utils.config import ConfigManager
from ..utils.logging import setup_logging

# Import Database agent for A2A communication
try:
    from .database_agent import DatabaseAgent
except ImportError:
    DatabaseAgent = None


logger = logging.getLogger(__name__)


class BrowserbaseAgent:
    """Agent for web automation and data extraction using Browserbase MCP server."""
    
    def __init__(
        self,
        llm: BaseLanguageModel,
        mcp_client: Optional[MCPToolboxClient] = None,
        database_agent: Optional[Any] = None,
        db_path: str = "data/web_extractions.db",
        browserbase_config: Optional[Dict] = None,
        hub_url: str = "http://localhost:5000/mcp",
        agent_port: int = 8001
    ):
        """
        Initialize the Browserbase agent.
        
        Args:
            llm: Language model for processing queries
            mcp_client: MCP client for tool communication
            database_agent: Database agent for A2A data storage
            db_path: Path to SQLite database for storing extractions (fallback)
            browserbase_config: Configuration for Browserbase connection
            hub_url: URL of the central MCP hub for registration and discovery
            agent_port: Port for this agent's MCP server
        """
        self.llm = llm
        self.mcp_client = mcp_client
        self.database_agent = database_agent
        self.db_path = Path(db_path)
        self.browserbase_config = browserbase_config or {}
        self.hub_url = hub_url
        self.agent_port = agent_port
        self.agent_id = f"browserbase-agent-{uuid.uuid4().hex[:8]}"
        
        # Hub integration
        self.registered_with_hub = False
        self.heartbeat_task: Optional[asyncio.Task] = None
        
        # Initialize database (fallback if no database agent)
        if not database_agent:
            self._setup_database()
            logger.warning("No Database agent provided - using direct SQLite fallback")
        else:
            logger.info("Using Database agent for A2A data storage")
        
        # Available tools
        self.tools = []
        self.session_id = None
        self.context_id = None
        
        logger.info("BrowserbaseAgent initialized")
    
    def _setup_database(self):
        """Set up SQLite database for storing web extractions."""
        # Create directory if it doesn't exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create database tables
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Web extractions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    extracted_data TEXT,
                    extraction_type TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            # Browser sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS browser_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE,
                    context_id TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """)
            
            # Screenshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS screenshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    screenshot_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            
            conn.commit()
        
        logger.info(f"Database initialized at {self.db_path}")
    
    async def initialize(self):
        """Initialize the agent and load available tools."""
        try:
            if self.mcp_client:
                # Load Browserbase tools
                self.tools = await self._load_browserbase_tools()
                logger.info(f"Loaded {len(self.tools)} Browserbase tools")
            else:
                logger.warning("No MCP client provided - using mock tools")
                self.tools = self._get_mock_tools()
            
            # Create initial browser session
            await self._create_browser_session()
            
        except Exception as e:
            logger.error(f"Failed to initialize BrowserbaseAgent: {e}")
            raise
    
    async def _load_browserbase_tools(self) -> List[Dict]:
        """Load available Browserbase tools from MCP server."""
        try:
            # This would connect to the actual Browserbase MCP server
            tools = await self.mcp_client.load_toolset("browserbase")
            return tools
        except Exception as e:
            logger.error(f"Failed to load Browserbase tools: {e}")
            return self._get_mock_tools()
    
    def _get_mock_tools(self) -> List[Dict]:
        """Get mock tools for testing without actual Browserbase connection."""
        return [
            {
                "name": "browserbase_session_create",
                "description": "Create a new browser session"
            },
            {
                "name": "browserbase_goto",
                "description": "Navigate to a URL"
            },
            {
                "name": "browserbase_screenshot",
                "description": "Take a screenshot of the current page"
            },
            {
                "name": "browserbase_get_page_content",
                "description": "Extract content from the current page"
            },
            {
                "name": "browserbase_click",
                "description": "Click on an element"
            },
            {
                "name": "browserbase_type",
                "description": "Type text into an element"
            },
            {
                "name": "browserbase_extract_data",
                "description": "Extract structured data from page"
            }
        ]
    
    async def _create_browser_session(self):
        """Create a new browser session."""
        try:
            if self.mcp_client:
                # Create actual session
                session_data = await self.mcp_client.execute_tool(
                    "browserbase_session_create",
                    {
                        "width": 1920,
                        "height": 1080,
                        "persist": True
                    }
                )
                self.session_id = session_data.get("session_id")
            else:
                # Mock session
                self.session_id = f"mock_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Store session in database using Database agent or fallback
            await self._store_browser_session(
                session_id=self.session_id,
                context_id=self.context_id,
                status="active"
            )
            
            logger.info(f"Browser session created: {self.session_id}")
            
        except Exception as e:
            logger.error(f"Failed to create browser session: {e}")
            raise
    
    async def extract_website_data(
        self,
        url: str,
        extraction_type: str = "general",
        selectors: Optional[Dict] = None,
        take_screenshot: bool = True
    ) -> Dict[str, Any]:
        """
        Extract data from a website.
        
        Args:
            url: URL to extract data from
            extraction_type: Type of extraction (general, table, form, etc.)
            selectors: CSS selectors for specific elements
            take_screenshot: Whether to take a screenshot
            
        Returns:
            Dictionary containing extracted data
        """
        try:
            logger.info(f"Extracting data from {url}")
            
            # Navigate to URL
            await self._navigate_to_url(url)
            
            # Take screenshot if requested
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(url)
            
            # Extract page content
            page_content = await self._extract_page_content()
            
            # Extract structured data based on type
            structured_data = await self._extract_structured_data(
                extraction_type, selectors
            )
            
            # Store in database
            extraction_id = await self._store_extraction(
                url=url,
                title=page_content.get("title", ""),
                content=page_content.get("content", ""),
                structured_data=structured_data,
                extraction_type=extraction_type,
                screenshot_path=screenshot_path
            )
            
            result = {
                "extraction_id": extraction_id,
                "url": url,
                "title": page_content.get("title", ""),
                "content": page_content.get("content", ""),
                "structured_data": structured_data,
                "extraction_type": extraction_type,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Data extraction completed for {url}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract data from {url}: {e}")
            raise
    
    async def _navigate_to_url(self, url: str):
        """Navigate to a URL."""
        try:
            if self.mcp_client:
                await self.mcp_client.execute_tool(
                    "browserbase_goto",
                    {
                        "session_id": self.session_id,
                        "url": url
                    }
                )
            else:
                # Mock navigation
                await asyncio.sleep(0.1)
                logger.info(f"Mock navigation to {url}")
                
        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            raise
    
    async def _take_screenshot(self, url: str) -> Optional[str]:
        """Take a screenshot of the current page."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_filename = f"screenshot_{timestamp}.png"
            screenshot_path = Path("data/screenshots") / screenshot_filename
            
            # Create directory if it doesn't exist
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            
            if self.mcp_client:
                screenshot_data = await self.mcp_client.execute_tool(
                    "browserbase_screenshot",
                    {
                        "session_id": self.session_id,
                        "full_page": True
                    }
                )
                
                # Save screenshot
                if screenshot_data.get("image_data"):
                    import base64
                    with open(screenshot_path, "wb") as f:
                        f.write(base64.b64decode(screenshot_data["image_data"]))
            else:
                # Mock screenshot
                with open(screenshot_path, "w") as f:
                    f.write(f"Mock screenshot for {url}")
            
            # Store in database
            await self._store_screenshot(
                url=url,
                screenshot_path=str(screenshot_path),
                metadata={"session_id": self.session_id}
            )
            
            return str(screenshot_path)
            
        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None
    
    async def _extract_page_content(self) -> Dict[str, Any]:
        """Extract general page content."""
        try:
            if self.mcp_client:
                content_data = await self.mcp_client.execute_tool(
                    "browserbase_get_page_content",
                    {
                        "session_id": self.session_id,
                        "include_title": True,
                        "include_text": True,
                        "include_links": True
                    }
                )
                return content_data
            else:
                # Mock content extraction
                return {
                    "title": "Mock Page Title",
                    "content": "Mock page content extracted from the website",
                    "links": ["https://example.com/link1", "https://example.com/link2"],
                    "text_length": 150
                }
                
        except Exception as e:
            logger.error(f"Failed to extract page content: {e}")
            return {}
    
    async def _extract_structured_data(
        self,
        extraction_type: str,
        selectors: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Extract structured data based on type and selectors."""
        try:
            if extraction_type == "table":
                return await self._extract_table_data()
            elif extraction_type == "form":
                return await self._extract_form_data()
            elif extraction_type == "product":
                return await self._extract_product_data()
            elif extraction_type == "article":
                return await self._extract_article_data()
            elif extraction_type == "stock":
                return await self._extract_stock_data()
            elif extraction_type == "custom" and selectors:
                return await self._extract_custom_data(selectors)
            else:
                return await self._extract_general_data()
                
        except Exception as e:
            logger.error(f"Failed to extract structured data: {e}")
            return {}
    
    async def _extract_table_data(self) -> Dict[str, Any]:
        """Extract table data from the page."""
        # Mock table extraction
        return {
            "tables": [
                {
                    "headers": ["Column 1", "Column 2", "Column 3"],
                    "rows": [
                        ["Row 1 Col 1", "Row 1 Col 2", "Row 1 Col 3"],
                        ["Row 2 Col 1", "Row 2 Col 2", "Row 2 Col 3"]
                    ]
                }
            ]
        }
    
    async def _extract_form_data(self) -> Dict[str, Any]:
        """Extract form data from the page."""
        # Mock form extraction
        return {
            "forms": [
                {
                    "action": "/submit",
                    "method": "POST",
                    "fields": [
                        {"name": "username", "type": "text", "required": True},
                        {"name": "email", "type": "email", "required": True},
                        {"name": "message", "type": "textarea", "required": False}
                    ]
                }
            ]
        }
    
    async def _extract_product_data(self) -> Dict[str, Any]:
        """Extract product data from the page."""
        # Mock product extraction
        return {
            "products": [
                {
                    "name": "Sample Product",
                    "price": "$29.99",
                    "description": "High-quality sample product",
                    "availability": "In Stock",
                    "rating": 4.5,
                    "reviews": 123
                }
            ]
        }
    
    async def _extract_article_data(self) -> Dict[str, Any]:
        """Extract article data from the page."""
        # Mock article extraction
        return {
            "articles": [
                {
                    "title": "Sample Article Title",
                    "author": "John Doe",
                    "date": "2024-01-15",
                    "content": "Sample article content...",
                    "tags": ["technology", "ai", "automation"]
                }
            ]
        }
    
    async def _extract_custom_data(self, selectors: Dict) -> Dict[str, Any]:
        """Extract custom data using provided selectors."""
        # Mock custom extraction
        return {
            "custom_data": {
                selector: f"Mock data for {selector}"
                for selector in selectors.keys()
            }
        }
    
    async def _extract_general_data(self) -> Dict[str, Any]:
        """Extract general structured data."""
        return {
            "meta_data": {
                "description": "Sample meta description",
                "keywords": ["sample", "web", "extraction"],
                "og_title": "Sample Open Graph Title",
                "og_description": "Sample Open Graph Description"
            },
            "headings": {
                "h1": ["Main Heading"],
                "h2": ["Subheading 1", "Subheading 2"],
                "h3": ["Sub-subheading 1", "Sub-subheading 2"]
            }
        }
    
    async def _store_extraction(
        self,
        url: str,
        title: str,
        content: str,
        structured_data: Dict,
        extraction_type: str,
        screenshot_path: Optional[str] = None
    ) -> Any:
        """Store extraction data using Database agent (A2A), fallback to SQLite if not available."""
        metadata = {
            "session_id": self.session_id,
            "screenshot_path": screenshot_path,
            "extraction_settings": {
                "type": extraction_type
            }
        }
        try:
            if self.database_agent:
                # Use A2A protocol: call Database agent's method
                # The method name and parameters may need to be adapted to your DatabaseAgent API
                # Here we assume an async method 'store_extraction' exists
                result = await self.database_agent.store_extraction(
                    url=url,
                    title=title,
                    content=content,
                    extracted_data=structured_data,
                    extraction_type=extraction_type,
                    metadata=metadata
                )
                logger.info(f"Extraction stored via Database agent: {result}")
                return result
            else:
                # Fallback: store directly in SQLite
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO web_extractions 
                        (url, title, content, extracted_data, extraction_type, metadata)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        url,
                        title,
                        content,
                        json.dumps(structured_data),
                        extraction_type,
                        json.dumps(metadata)
                    ))
                    extraction_id = cursor.lastrowid
                    conn.commit()
                    logger.info(f"Extraction stored with ID: {extraction_id}")
                    return extraction_id
        except Exception as e:
            logger.error(f"Failed to store extraction: {e}")
            raise
    
    async def query_extractions(
        self,
        url_pattern: Optional[str] = None,
        extraction_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict]:
        """Query stored extractions from database using Database agent (A2A), fallback to SQLite."""
        try:
            if self.database_agent:
                # Use A2A protocol: call Database agent's method
                query = "SELECT * FROM web_extractions WHERE 1=1"
                params = []
                
                if url_pattern:
                    query += " AND url LIKE %s"
                    params.append(f"%{url_pattern}%")
                
                if extraction_type:
                    query += " AND extraction_type = %s"
                    params.append(extraction_type)
                
                query += " ORDER BY timestamp DESC LIMIT %s"
                params.append(limit)
                
                results = await self.database_agent.execute_query(query, params)
                logger.info(f"Retrieved {len(results) if results else 0} extractions via Database agent")
                
                # Process results to parse JSON fields
                processed_results = []
                if results:
                    for row in results:
                        extraction = dict(row) if hasattr(row, 'keys') else row
                        # Parse JSON fields if they exist
                        if isinstance(extraction, dict):
                            if extraction.get("extracted_data") and isinstance(extraction["extracted_data"], str):
                                try:
                                    extraction["extracted_data"] = json.loads(extraction["extracted_data"])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                            if extraction.get("metadata") and isinstance(extraction["metadata"], str):
                                try:
                                    extraction["metadata"] = json.loads(extraction["metadata"])
                                except (json.JSONDecodeError, TypeError):
                                    pass
                        processed_results.append(extraction)
                
                return processed_results
            else:
                # Fallback: query SQLite directly
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    
                    query = "SELECT * FROM web_extractions WHERE 1=1"
                    params = []
                    
                    if url_pattern:
                        query += " AND url LIKE ?"
                        params.append(f"%{url_pattern}%")
                    
                    if extraction_type:
                        query += " AND extraction_type = ?"
                        params.append(extraction_type)
                    
                    query += " ORDER BY timestamp DESC LIMIT ?"
                    params.append(limit)
                    
                    cursor.execute(query, params)
                    rows = cursor.fetchall()
                    
                    # Convert to dictionaries
                    columns = [desc[0] for desc in cursor.description]
                    results = []
                    
                    for row in rows:
                        extraction = dict(zip(columns, row))
                        # Parse JSON fields
                        if extraction.get("extracted_data"):
                            extraction["extracted_data"] = json.loads(extraction["extracted_data"])
                        if extraction.get("metadata"):
                            extraction["metadata"] = json.loads(extraction["metadata"])
                        results.append(extraction)
                    
                    return results
                
        except Exception as e:
            logger.error(f"Failed to query extractions: {e}")
            return []
    
    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process a natural language query for web extraction."""
        try:
            logger.info(f"Processing query: {query}")
            
            # Use LLM to understand the query and determine action
            messages = [
                HumanMessage(content=f"""
                Analyze this web extraction query and determine the best action:
                
                Query: {query}
                
                Available actions:
                1. extract_website_data - Extract data from a specific URL
                2. query_extractions - Search existing extractions
                3. take_screenshot - Take a screenshot of a website
                4. general_web_search - General web search and extraction
                
                Respond with JSON containing:
                - action: The action to take
                - parameters: Parameters for the action
                - url: URL if applicable
                - extraction_type: Type of extraction if applicable
                
                Examples:
                - "Extract product info from amazon.com" -> action: extract_website_data, url: amazon.com, extraction_type: product
                - "Show me previous extractions from news sites" -> action: query_extractions, url_pattern: news
                - "Take a screenshot of google.com" -> action: take_screenshot, url: google.com
                """)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Parse LLM response
            try:
                action_plan = json.loads(response.content)
            except json.JSONDecodeError:
                # Fallback parsing
                action_plan = {
                    "action": "extract_website_data",
                    "parameters": {"url": "https://example.com"},
                    "extraction_type": "general"
                }
            
            # Execute the planned action
            result = await self._execute_action(action_plan)
            
            return {
                "query": query,
                "action_plan": action_plan,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to process query: {e}")
            return {
                "query": query,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _execute_action(self, action_plan: Dict) -> Dict[str, Any]:
        """Execute the planned action."""
        action = action_plan.get("action")
        parameters = action_plan.get("parameters", {})
        
        if action == "extract_website_data":
            url = parameters.get("url") or action_plan.get("url")
            extraction_type = parameters.get("extraction_type") or action_plan.get("extraction_type", "general")
            
            return await self.extract_website_data(
                url=url,
                extraction_type=extraction_type
            )
        
        elif action == "query_extractions":
            url_pattern = parameters.get("url_pattern")
            extraction_type = parameters.get("extraction_type")
            limit = parameters.get("limit", 10)
            
            extractions = await self.query_extractions(
                url_pattern=url_pattern,
                extraction_type=extraction_type,
                limit=limit
            )
            
            return {
                "extractions": extractions,
                "count": len(extractions)
            }
        
        elif action == "take_screenshot":
            url = parameters.get("url") or action_plan.get("url")
            await self._navigate_to_url(url)
            screenshot_path = await self._take_screenshot(url)
            
            return {
                "url": url,
                "screenshot_path": screenshot_path
            }
        
        else:
            return {"error": f"Unknown action: {action}"}
    
    async def cleanup(self):
        """Clean up resources and close connections."""
        try:
            if self.session_id:
                # Mark session as closed using Database agent or fallback
                if self.database_agent:
                    # Use A2A protocol: call Database agent's method
                    query = """
                    UPDATE browser_sessions 
                    SET status = %s 
                    WHERE session_id = %s
                    """
                    await self.database_agent.execute_query(
                        query, 
                        ["closed", self.session_id]
                    )
                    logger.info(f"Session {self.session_id} marked as closed via Database agent")
                else:
                    # Fallback: update SQLite directly
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        cursor.execute("""
                            UPDATE browser_sessions 
                            SET status = 'closed' 
                            WHERE session_id = ?
                        """, (self.session_id,))
                        conn.commit()
                    logger.info(f"Session {self.session_id} marked as closed in SQLite")
            
            if self.mcp_client:
                await self.mcp_client.close()
            
            logger.info("BrowserbaseAgent cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def _extract_stock_data(
        self,
        url: str = "https://finance.yahoo.com/sectors/technology/semiconductors/",
        take_screenshot: bool = True
    ) -> Dict[str, Any]:
        """
        Extract stock data from Yahoo Finance semiconductors page.
        
        Args:
            url: URL to extract stock data from (defaults to Yahoo Finance semiconductors)
            take_screenshot: Whether to take a screenshot
            
        Returns:
            Dictionary containing extracted stock data
        """
        try:
            logger.info(f"Extracting stock data from {url}")
            
            # Navigate to URL
            await self._navigate_to_url(url)
            
            # Take screenshot if requested
            screenshot_path = None
            if take_screenshot:
                screenshot_path = await self._take_screenshot(url)
            
            # Extract page content
            page_content = await self._extract_page_content()
            
            # Extract stock-specific data
            stock_data = await self._extract_stock_specific_data()
            
            # Store in database
            extraction_id = await self._store_extraction(
                url=url,
                title=page_content.get("title", "Yahoo Finance - Semiconductors"),
                content=page_content.get("content", ""),
                structured_data=stock_data,
                extraction_type="stock_data",
                screenshot_path=screenshot_path
            )
            
            result = {
                "extraction_id": extraction_id,
                "url": url,
                "title": page_content.get("title", "Yahoo Finance - Semiconductors"),
                "content": page_content.get("content", ""),
                "stock_data": stock_data,
                "extraction_type": "stock_data",
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Stock data extraction completed for {url}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract stock data from {url}: {e}")
            raise

    async def _extract_stock_specific_data(self) -> Dict[str, Any]:
        """Extract stock-specific data from Yahoo Finance page."""
        try:
            if self.mcp_client:
                # Use real MCP client to extract structured data
                stock_data = await self.mcp_client.execute_tool(
                    "browserbase_extract_data",
                    {
                        "session_id": self.session_id,
                        "selectors": {
                            "stock_table": "table[data-testid='screener-table']",
                            "stock_rows": "tr[data-testid='screener-row']",
                            "stock_names": "td[data-testid='screener-name']",
                            "stock_prices": "td[data-testid='screener-price']",
                            "stock_changes": "td[data-testid='screener-change']",
                            "stock_volumes": "td[data-testid='screener-volume']"
                        }
                    }
                )
                return stock_data
            else:
                # Mock stock data for testing
                return {
                    "semiconductor_stocks": [
                        {
                            "symbol": "NVDA",
                            "name": "NVIDIA Corporation",
                            "price": "$875.50",
                            "change": "+12.45",
                            "change_percent": "+1.44%",
                            "volume": "45,678,900",
                            "market_cap": "2.16T",
                            "pe_ratio": "65.23"
                        },
                        {
                            "symbol": "AMD",
                            "name": "Advanced Micro Devices",
                            "price": "$145.75",
                            "change": "-2.30",
                            "change_percent": "-1.55%",
                            "volume": "28,456,100",
                            "market_cap": "235.6B",
                            "pe_ratio": "42.18"
                        },
                        {
                            "symbol": "INTC",
                            "name": "Intel Corporation",
                            "price": "$32.85",
                            "change": "+0.85",
                            "change_percent": "+2.66%",
                            "volume": "67,890,200",
                            "market_cap": "140.2B",
                            "pe_ratio": "15.67"
                        },
                        {
                            "symbol": "TSM",
                            "name": "Taiwan Semiconductor",
                            "price": "$105.20",
                            "change": "+3.15",
                            "change_percent": "+3.09%",
                            "volume": "15,234,500",
                            "market_cap": "545.8B",
                            "pe_ratio": "22.45"
                        },
                        {
                            "symbol": "QCOM",
                            "name": "Qualcomm Incorporated",
                            "price": "$165.90",
                            "change": "-1.20",
                            "change_percent": "-0.72%",
                            "volume": "8,567,300",
                            "market_cap": "185.4B",
                            "pe_ratio": "18.92"
                        }
                    ],
                    "sector_summary": {
                        "total_stocks": 5,
                        "market_cap_total": "3.27T",
                        "avg_pe_ratio": "32.89",
                        "top_performer": "TSM (+3.09%)",
                        "worst_performer": "AMD (-1.55%)"
                    },
                    "extraction_metadata": {
                        "page_title": "Yahoo Finance - Technology Semiconductors",
                        "extraction_time": datetime.now().isoformat(),
                        "data_source": "Yahoo Finance",
                        "url": "https://finance.yahoo.com/sectors/technology/semiconductors/"
                    }
                }
                
        except Exception as e:
            logger.error(f"Failed to extract stock-specific data: {e}")
            return {}
    
    def _extract_text_content(self, content: str) -> str:
        """Extract clean text content from HTML."""
        import re
        # Remove HTML tags and extra whitespace
        clean_text = re.sub(r'<[^>]+>', '', str(content))
        return clean_text.strip()
    
    def _extract_price(self, price_str: str) -> Optional[float]:
        """Extract price from string."""
        try:
            import re
            # Extract number from price string (e.g., "$123.45" -> 123.45)
            price_match = re.search(r'[\d,]+\.?\d*', str(price_str).replace(',', ''))
            if price_match:
                return float(price_match.group())
            return None
        except:
            return None
    
    def _extract_percentage(self, percent_str: str) -> Optional[float]:
        """Extract percentage from string."""
        try:
            import re
            # Extract percentage (e.g., "+1.23%" -> 1.23)
            percent_match = re.search(r'[+-]?[\d.]+', str(percent_str))
            if percent_match:
                return float(percent_match.group())
            return None
        except:
            return None
    
    def _extract_volume(self, volume_str: str) -> Optional[int]:
        """Extract volume from string."""
        try:
            import re
            # Handle volume formats like "1.23M", "456K", "789"
            volume_clean = str(volume_str).replace(',', '')
            if 'M' in volume_clean:
                num = float(re.search(r'[\d.]+', volume_clean).group())
                return int(num * 1000000)
            elif 'K' in volume_clean:
                num = float(re.search(r'[\d.]+', volume_clean).group())
                return int(num * 1000)
            elif 'B' in volume_clean:
                num = float(re.search(r'[\d.]+', volume_clean).group())
                return int(num * 1000000000)
            else:
                return int(float(re.search(r'[\d]+', volume_clean).group()))
        except:
            return None
    
    def _extract_market_cap(self, market_cap_str: str) -> str:
        """Extract market cap from string."""
        try:
            import re
            # Extract market cap (e.g., "$123.45B" -> "123.45B")
            cap_match = re.search(r'[\d.]+[KMBT]?', str(market_cap_str))
            if cap_match:
                return cap_match.group()
            return str(market_cap_str)
        except:
            return str(market_cap_str)

    async def register_with_hub(self) -> bool:
        """Register this agent with the central MCP hub."""
        try:
            import aiohttp
            
            registration_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "BrowserbaseAgent",
                    "agent_type": "web_automation",
                    "endpoint_url": f"http://localhost:{self.agent_port}",
                    "capabilities": [
                        {
                            "name": "extract_website_data",
                            "description": "Extract structured data from websites",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "extraction_type": {"type": "string"}
                                },
                                "required": ["url"]
                            },
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "extraction_id": {"type": "integer"},
                                    "data": {"type": "object"},
                                    "timestamp": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "take_screenshot",
                            "description": "Take screenshot of a webpage",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "url": {"type": "string"},
                                    "options": {"type": "object"}
                                },
                                "required": ["url"]
                            },
                            "output_schema": {
                                "type": "object",
                                "properties": {
                                    "screenshot_path": {"type": "string"},
                                    "url": {"type": "string"}
                                }
                            }
                        },
                        {
                            "name": "query_extractions",
                            "description": "Query stored web extractions",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "limit": {"type": "integer"},
                                    "filters": {"type": "object"}
                                }
                            },
                            "output_schema": {
                                "type": "array",
                                "items": {"type": "object"}
                            }
                        }
                    ],
                    "metadata": {
                        "version": "1.0.0",
                        "description": "Web automation and data extraction agent",
                        "supported_protocols": ["browserbase", "playwright"]
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hub_url,
                    json=registration_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            self.registered_with_hub = True
                            logger.info(f"✅ Registered with MCP Hub: {self.agent_id}")
                            
                            # Start heartbeat
                            self.heartbeat_task = asyncio.create_task(self._send_heartbeats())
                            
                            return True
                    
                    logger.error(f"Failed to register with hub: {response.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Hub registration failed: {e}")
            return False
    
    async def _send_heartbeats(self):
        """Send periodic heartbeats to the hub."""
        try:
            import aiohttp
            
            while self.registered_with_hub:
                heartbeat_data = {
                    "jsonrpc": "2.0",
                    "id": str(uuid.uuid4()),
                    "method": "agents/heartbeat",
                    "params": {
                        "agent_id": self.agent_id,
                        "status": "active"
                    }
                }
                
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            self.hub_url,
                            json=heartbeat_data,
                            headers={"Content-Type": "application/json"}
                        ) as response:
                            if response.status == 200:
                                logger.debug(f"Heartbeat sent successfully: {self.agent_id}")
                            else:
                                logger.warning(f"Heartbeat failed: {response.status}")
                
                except Exception as e:
                    logger.error(f"Heartbeat error: {e}")
                
                # Wait 30 seconds before next heartbeat
                await asyncio.sleep(30)
        
        except asyncio.CancelledError:
            logger.info("Heartbeat task cancelled")
        except Exception as e:
            logger.error(f"Heartbeat task error: {e}")
    
    async def discover_agents(self, agent_type: Optional[str] = None, capability: Optional[str] = None) -> List[Dict[str, Any]]:
        """Discover other agents registered with the hub."""
        try:
            import aiohttp
            
            discovery_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/discover",
                "params": {
                    "agent_type": agent_type,
                    "capability": capability,
                    "status": "active"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hub_url,
                    json=discovery_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            agents = result["result"]["agents"]
                            logger.info(f"Discovered {len(agents)} agents")
                            return agents
            
            return []
        
        except Exception as e:
            logger.error(f"Agent discovery failed: {e}")
            return []
    
    async def call_agent(self, target_agent_id: str, method: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call another agent through the hub."""
        try:
            import aiohttp
            
            call_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/call",
                "params": {
                    "target_agent_id": target_agent_id,
                    "method": method,
                    "params": params
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hub_url,
                    json=call_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Called agent {target_agent_id}.{method} successfully")
                        return result
                    else:
                        logger.error(f"Agent call failed: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Agent call error: {e}")
            return None
    
    async def start_agent_server(self):
        """Start the agent's own MCP server for receiving calls."""
        try:
            from aiohttp import web
            import aiohttp_cors
            
            app = web.Application()
            
            # Setup CORS
            cors = aiohttp_cors.setup(app, defaults={
                "*": aiohttp_cors.ResourceOptions(
                    allow_credentials=True,
                    expose_headers="*",
                    allow_headers="*",
                    allow_methods="*"
                )
            })
            
            # Add MCP endpoint
            app.router.add_post('/mcp', self._handle_agent_request)
            
            # Add CORS
            for route in list(app.router.routes()):
                cors.add(route)
            
            # Start server
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, 'localhost', self.agent_port)
            await site.start()
            
            logger.info(f"🚀 Browserbase agent server started on port {self.agent_port}")
            return runner
        
        except Exception as e:
            logger.error(f"Failed to start agent server: {e}")
            return None
    
    async def _handle_agent_request(self, request):
        """Handle incoming MCP requests to this agent."""
        try:
            data = await request.json()
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Route to appropriate handler
            if method == "extract_website_data":
                result = await self.extract_website_data(
                    url=params.get("url"),
                    extraction_type=params.get("extraction_type", "general")
                )
            elif method == "take_screenshot":
                result = await self._take_screenshot(
                    url=params.get("url"),
                    options=params.get("options", {})
                )
            elif method == "query_extractions":
                result = await self.query_extractions(
                    limit=params.get("limit", 10)
                )
            else:
                return self._agent_error_response(f"Unknown method: {method}", -32601, request_id)
            
            return self._agent_success_response(result, request_id)
        
        except Exception as e:
            logger.error(f"Error handling agent request: {e}")
            return self._agent_error_response(f"Internal error: {str(e)}", -32603)
    
    def _agent_success_response(self, result: Any, request_id: Optional[str] = None):
        """Create a JSON-RPC 2.0 success response."""
        from aiohttp import web
        
        response_data = {
            "jsonrpc": "2.0",
            "result": result
        }
        
        if request_id is not None:
            response_data["id"] = request_id
        
        return web.json_response(response_data)
    
    def _agent_error_response(self, message: str, code: int = -32603, request_id: Optional[str] = None):
        """Create a JSON-RPC 2.0 error response."""
        from aiohttp import web
        
        response_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if request_id is not None:
            response_data["id"] = request_id
        
        return web.json_response(response_data, status=400 if code == -32600 else 200)
    
    async def shutdown(self):
        """Shutdown the agent and cleanup resources."""
        self.registered_with_hub = False
        
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        logger.info(f"Browserbase agent {self.agent_id} shutdown complete")
