#!/usr/bin/env python3
"""
Browserbase Agent Server Launcher
================================

Starts the Browserbase agent as an MCP server on port 8001.
This agent provides web automation and data extraction capabilities.
"""

import asyncio
import logging
import sys
import os
import time
import json
from datetime import datetime
from pathlib import Path
import base64
from urllib.parse import urlparse
import aiohttp
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Browserbase API configuration
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

print(f"🔑 BROWSERBASE_API_KEY loaded: {'✅ Yes' if BROWSERBASE_API_KEY else '❌ No'}")
print(f"🏗️  BROWSERBASE_PROJECT_ID loaded: {'✅ Yes' if BROWSERBASE_PROJECT_ID else '❌ No'}")

# Import simplified versions to avoid complex dependencies
import sys
import os
from pathlib import Path
import json
import logging
from datetime import datetime
import sqlite3
import uuid

# Simple LLM mock for testing
class MockLLM:
    async def ainvoke(self, messages):
        class MockResponse:
            def __init__(self):
                self.content = '{"action": "extract_website_data", "url": "https://example.com", "extraction_type": "general"}'
        return MockResponse()

# Simplified Browserbase Agent for testing
class SimpleBrowserbaseAgent:
    def __init__(self, port=8001):
        self.port = port
        self.session_id = None  # Will be created per request
        
        # Only create database for storing extraction metadata, not as primary storage
        self.db_path = Path("data/browserbase_extractions.db")
        self.screenshots_dir = Path("data/screenshots")
        self._setup_database()
        self._setup_screenshots_dir()
        
        # Check API credentials on startup
        if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
            logger.warning("⚠️  Browserbase API credentials not configured!")
            logger.warning("   Set BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID environment variables")
            logger.warning("   Falling back to local Playwright extraction")
        else:
            logger.info(f"✅ Browserbase API configured with project: {BROWSERBASE_PROJECT_ID}")
        
    def _setup_screenshots_dir(self):
        """Create screenshots directory if it doesn't exist"""
        self.screenshots_dir.mkdir(parents=True, exist_ok=True)
        logging.info(f"Screenshots directory ready: {self.screenshots_dir}")
        
    def _setup_database(self):
        """Setup SQLite database"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS web_extractions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    extracted_data TEXT,
                    extraction_type TEXT,
                    screenshot_path TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    metadata TEXT
                )
            """)
            # Add screenshot_path column if it doesn't exist (for existing databases)
            cursor.execute("""
                SELECT name FROM pragma_table_info('web_extractions') WHERE name='screenshot_path'
            """)
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE web_extractions ADD COLUMN screenshot_path TEXT")
            conn.commit()
    
    async def initialize(self):
        """Initialize agent"""
        if BROWSERBASE_API_KEY and BROWSERBASE_PROJECT_ID:
            logger.info("🚀 Browserbase agent initialized with API integration")
        else:
            logger.warning("⚠️  Browserbase agent initialized in local mode (no API credentials)")
        
    async def extract_website_data(self, url, extraction_type="general", selectors=None, take_screenshot=True):
        """Enhanced website data extraction with real data and screenshots"""
        
        logger.info(f"🌍 Starting extraction for: {url}")
        
        # Try to extract real data first
        real_data = await self._extract_real_data(url)
        
        if real_data and real_data.get('success'):
            logger.info(f"✅ Real data extraction successful for: {url}")
            # Use real extracted data
            extraction_data = {
                "extraction_id": str(uuid.uuid4()),
                "url": url,
                "title": real_data.get('title', f"Extracted Data from {url}"),
                "content": real_data.get('content', f"Successfully extracted content from {url}"),
                "structured_data": real_data.get('metadata', {}),
                "screenshot_path": real_data.get('screenshot_path'),
                "extraction_method": real_data.get('extraction_method', 'browserbase_api'),
                "timestamp": real_data.get('timestamp', time.time()),
                "raw_data": real_data
            }
        else:
            logger.error(f"❌ Real data extraction failed for: {url}")
            logger.error("   This should not happen in production mode!")
            raise Exception(f"Failed to extract real data from {url}. Check Browserbase API configuration and network connectivity.")
            
        # Store in local database for backup/reference
        await self._store_extraction(extraction_data)
        
        return extraction_data

    async def _store_extraction(self, extraction_data):
        """Store extraction data in local SQLite database for backup/reference"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO web_extractions (url, title, content, extracted_data, extraction_type, screenshot_path, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    extraction_data.get("url", ""),
                    extraction_data.get("title", ""),
                    extraction_data.get("content", ""),
                    json.dumps(extraction_data.get("structured_data", {})),
                    "general",  # extraction_type
                    extraction_data.get("screenshot_path"),
                    json.dumps({"extraction_method": extraction_data.get("extraction_method", "unknown")})
                ))
                conn.commit()
                logger.info(f"📝 Stored extraction backup in local database")
        except Exception as e:
            logger.warning(f"Failed to store extraction backup: {e}")
            
    async def _capture_screenshot(self, url, extraction_id):
        """Capture screenshot (legacy method - screenshots now handled by Browserbase API)"""
        logger.info("Screenshot capture handled by Browserbase API")
        return None
        
    
    async def _capture_screenshot(self, url, extraction_id=None):
        """Capture real screenshot of a webpage using Playwright"""
        try:
            # Create a unique filename
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.replace(".", "_")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{domain}_{timestamp}"
            if extraction_id:
                filename = f"{extraction_id}_{filename}"
            screenshot_path = self.screenshots_dir / f"{filename}.png"
            
            # Use Playwright to capture real screenshot
            try:
                async with async_playwright() as p:
                    # Launch browser
                    browser = await p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-dev-shm-usage']
                    )
                    
                    # Create new page
                    page = await browser.new_page()
                    
                    # Set viewport size
                    await page.set_viewport_size({'width': 1200, 'height': 800})
                    
                    # Navigate to URL with timeout
                    await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    
                    # Wait a moment for dynamic content
                    await page.wait_for_timeout(2000)
                    
                    # Take screenshot
                    await page.screenshot(
                        path=str(screenshot_path),
                        full_page=True
                    )
                    
                    # Close browser
                    await browser.close()
                    
                    logging.info(f"Real screenshot captured for {url} -> {screenshot_path}")
                    return str(screenshot_path)
                    
            except Exception as playwright_error:
                logging.warning(f"Playwright screenshot failed for {url}: {playwright_error}")
                # Fallback to mock screenshot
                await self._create_mock_screenshot(screenshot_path, url)
                return str(screenshot_path)
            
        except Exception as e:
            logging.error(f"Error capturing screenshot for {url}: {e}")
            return None
    
    async def _extract_real_data(self, url):
        """Extract real data from webpage using Browserbase API"""
        try:
            if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
                logger.warning("Browserbase API credentials not configured, falling back to local Playwright")
                return await self._extract_with_playwright(url)
            
            logger.info(f"🌍 Extracting real data from {url} using Browserbase API...")
            
            # Create Browserbase session
            session_data = await self._create_browserbase_session()
            if not session_data:
                logger.error("❌ Failed to create Browserbase session")
                logger.info("🔧 Falling back to local Playwright extraction...")
                return await self._extract_with_playwright(url)
            
            session_id = session_data.get('id')
            logger.info(f"✅ Created Browserbase session: {session_id}")
            
            # Navigate and extract data using Browserbase
            extraction_result = await self._extract_via_browserbase_session(session_id, url)
            
            # Terminate session
            await self._terminate_browserbase_session(session_id)
            
            return extraction_result
            
        except Exception as e:
            logger.error(f"❌ Browserbase extraction failed: {e}")
            logger.info("🔧 Falling back to local Playwright extraction...")
            return await self._extract_with_playwright(url)
    
    async def _create_browserbase_session(self):
        """Create a new Browserbase session"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-BB-API-Key': BROWSERBASE_API_KEY,
                    'Content-Type': 'application/json'
                }
                
                data = {
                    'projectId': BROWSERBASE_PROJECT_ID
                }
                
                async with session.post(
                    'https://www.browserbase.com/v1/sessions',
                    headers=headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"Failed to create Browserbase session: HTTP {response.status}")
                        return None
                        
        except Exception as e:
            logger.error(f"Error creating Browserbase session: {e}")
            return None
    
    async def _extract_via_browserbase_session(self, session_id, url):
        """Extract data using an active Browserbase session"""
        try:
            # Use Playwright to connect to remote Browserbase session
            async with async_playwright() as p:
                browser = await p.chromium.connect_over_cdp(
                    f"wss://connect.browserbase.com?apiKey={BROWSERBASE_API_KEY}&sessionId={session_id}"
                )
                
                page = browser.contexts[0].pages[0]
                
                # Navigate to URL
                await page.goto(url, wait_until='domcontentloaded', timeout=60000)
                await page.wait_for_timeout(3000)
                
                # Extract comprehensive data
                title = await page.title()
                
                # Take screenshot
                screenshot_path = None
                try:
                    screenshot_dir = Path("data/screenshots")
                    screenshot_dir.mkdir(exist_ok=True)
                    timestamp = int(time.time())
                    domain = urlparse(url).netloc.replace('.', '_')
                    screenshot_path = screenshot_dir / f"{domain}_{timestamp}.png"
                    
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"📸 Screenshot saved: {screenshot_path}")
                except Exception as e:
                    logger.warning(f"Failed to take screenshot: {e}")
                
                # Extract content
                content = await page.evaluate('''
                    () => {
                        // Remove script and style elements
                        const scripts = document.querySelectorAll('script, style');
                        scripts.forEach(el => el.remove());
                        
                        // Get visible text content
                        const body = document.body;
                        return body ? body.innerText.trim().substring(0, 2000) : '';
                    }
                ''')
                
                # Extract metadata
                metadata = await page.evaluate('''
                    () => {
                        const meta = {};
                        
                        // Get meta tags
                        document.querySelectorAll('meta').forEach(tag => {
                            const name = tag.getAttribute('name') || tag.getAttribute('property');
                            const content = tag.getAttribute('content');
                            if (name && content) {
                                meta[name] = content;
                            }
                        });
                        
                        // Get links
                        const links = Array.from(document.querySelectorAll('a[href]'))
                            .map(a => ({
                                text: a.textContent.trim(),
                                href: a.href
                            }))
                            .filter(link => link.text && link.href)
                            .slice(0, 20);
                        
                        // Get headings
                        const headings = Array.from(document.querySelectorAll('h1, h2, h3'))
                            .map(h => ({
                                level: h.tagName.toLowerCase(),
                                text: h.textContent.trim()
                            }))
                            .filter(h => h.text)
                            .slice(0, 10);
                        
                        return {
                            meta: meta,
                            links: links,
                            headings: headings,
                            url: window.location.href
                        };
                    }
                ''')
                
                await browser.close()
                
                return {
                    'url': url,
                    'title': title,
                    'content': content,
                    'metadata': metadata,
                    'screenshot_path': str(screenshot_path) if screenshot_path else None,
                    'extraction_method': 'browserbase_api',
                    'timestamp': time.time(),
                    'success': True
                }
                
        except Exception as e:
            logger.error(f"Error extracting data via Browserbase session: {e}")
            return None
    
    async def _terminate_browserbase_session(self, session_id):
        """Terminate a Browserbase session"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    'X-BB-API-Key': BROWSERBASE_API_KEY
                }
                
                async with session.delete(
                    f'https://www.browserbase.com/v1/sessions/{session_id}',
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        logger.info(f"✅ Terminated Browserbase session: {session_id}")
                    else:
                        logger.warning(f"Failed to terminate session {session_id}: HTTP {response.status}")
                        
        except Exception as e:
            logger.error(f"Error terminating Browserbase session: {e}")
    
    async def _extract_with_playwright(self, url):
        """Fallback extraction using local Playwright"""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to URL
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)

                # Capture screenshot first
                screenshot_path = None
                try:
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.replace(".", "_")
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    screenshot_filename = f"{domain}_{timestamp}.png"
                    screenshot_path = Path("data/screenshots") / screenshot_filename
                    
                    # Ensure screenshots directory exists
                    screenshot_path.parent.mkdir(exist_ok=True)
                    
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    logger.info(f"📸 Real screenshot captured: {screenshot_path}")
                except Exception as screenshot_error:
                    logger.warning(f"Failed to capture screenshot: {screenshot_error}")
                    screenshot_path = None

                # Extract basic page info
                title = await page.title()
                
                # Extract text content
                content = await page.evaluate('''
                    () => {
                        // Remove script and style elements
                        const scripts = document.querySelectorAll('script, style');
                        scripts.forEach(el => el.remove());
                        
                        // Get main content
                        const body = document.body;
                        return body ? body.innerText.substring(0, 1000) : '';
                    }
                ''')
                
                # Extract links
                links = await page.evaluate('''
                    () => {
                        const links = Array.from(document.querySelectorAll('a[href]'));
                        return links.slice(0, 10).map(link => link.href);
                    }
                ''')
                
                await browser.close()

                # Return in expected format
                return {
                    'success': True,
                    'title': title,
                    'content': content.strip(),
                    'links': links,
                    'screenshot_path': str(screenshot_path) if screenshot_path else None,
                    'extraction_method': 'local_playwright',
                    'metadata': {
                        'content_length': len(content.strip()),
                        'links_count': len(links)
                    },
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.warning(f"Real data extraction failed for {url}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _create_mock_screenshot(self, screenshot_path, url):
        """Create a mock screenshot for demonstration purposes"""
        try:
            # Create a simple image with URL text
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a 1200x800 white image
            img = Image.new('RGB', (1200, 800), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add URL and timestamp as text
            try:
                # Try to use a default font
                font = ImageFont.load_default()
            except:
                font = None
            
            # Draw URL and info
            draw.text((50, 50), f"Screenshot of: {url}", fill='black', font=font)
            draw.text((50, 100), f"Captured: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill='black', font=font)
            draw.text((50, 150), "Mock screenshot - replace with real browser automation", fill='gray', font=font)
            
            # Add a simple border
            draw.rectangle([10, 10, 1190, 790], outline='black', width=2)
            
            # Save the image
            img.save(screenshot_path)
            
        except Exception as e:
            logging.error(f"Error creating mock screenshot: {e}")
            # Create a minimal fallback
            with open(screenshot_path, 'w') as f:
                f.write(f"Mock screenshot for {url} at {datetime.now().isoformat()}")
    
    async def query_extractions(self, url_pattern=None, extraction_type=None, limit=10):
        """Query stored extractions"""
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
            
            columns = [desc[0] for desc in cursor.description]
            results = []
            for row in rows:
                extraction = dict(zip(columns, row))
                if extraction.get("extracted_data"):
                    extraction["extracted_data"] = json.loads(extraction["extracted_data"])
                results.append(extraction)
            
            return results
    
    async def process_query(self, query):
        """Process natural language query"""
        return {
            "query": query,
            "action_plan": {"action": "extract_website_data", "url": "https://example.com"},
            "result": {"message": f"Mock response for: {query}"},
            "timestamp": datetime.now().isoformat()
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        logger.info("Browserbase agent cleanup complete")
from aiohttp import web
import aiohttp_cors
import json
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

class BrowserbaseAgentServer:
    """Browserbase agent MCP server"""
    
    def __init__(self, port: int = 8001, hub_url: str = "http://localhost:5000"):
        self.port = port
        self.hub_url = hub_url
        self.agent_id = f"browserbase_agent_{port}"
        self.agent = None
        self.app = None
        self.runner = None
        
    async def initialize_agent(self):
        """Initialize the Browserbase agent"""
        try:
            # Use simplified agent for testing
            self.agent = SimpleBrowserbaseAgent(port=self.port)
            await self.agent.initialize()
            logger.info("✅ Browserbase agent initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Browserbase agent: {e}")
            raise
    
    async def register_with_hub(self):
        """Register this agent with the MCP hub"""
        try:
            import aiohttp
            
            registration_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "Browserbase Web Extraction Agent",
                    "agent_type": "browserbase",
                    "endpoint_url": f"http://localhost:{self.port}",
                    "capabilities": [
                        {
                            "name": "extract_website_data",
                            "description": "Extract data from websites using browserbase automation",
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
                                    "status": {"type": "string"},
                                    "title": {"type": "string"},
                                    "content": {"type": "string"},
                                    "data": {"type": "object"}
                                }
                            }
                        }
                    ],
                    "metadata": {
                        "version": "1.0.0",
                        "description": "Web automation and data extraction capabilities"
                    }
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.hub_url}/mcp", json=registration_data, 
                                       timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            logger.info(f"✅ Successfully registered Browserbase agent: {result['result']}")
                            return True
                        else:
                            logger.error(f"❌ Hub registration failed: {result}")
                            return False
                    else:
                        logger.error(f"❌ Hub registration HTTP error: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Failed to register with hub: {e}")
            return False
    
    async def create_app(self):
        """Create the web application"""
        self.app = web.Application()
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*",
                allow_methods="*"
            )
        })
        
        # Add routes
        self.app.router.add_post('/mcp', self.handle_mcp_request)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/status', self.status_check)
        
        # Apply CORS to all routes
        for route in list(self.app.router.routes()):
            cors.add(route)
        
        logger.info("🌐 Web application configured")
    
    async def handle_mcp_request(self, request):
        """Handle MCP requests"""
        try:
            data = await request.json()
            logger.info(f"Received MCP request: {data.get('method')}")
            
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            # Route to appropriate handler
            result = None
            
            if method == "ping":
                result = {
                    "status": "ok", 
                    "service": "browserbase_agent",
                    "port": self.port,
                    "timestamp": datetime.now().isoformat()
                }
            elif method == "tools/call":
                # Handle MCP tools/call method
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                
                if tool_name == "extract_website_data":
                    extraction_result = await self.agent.extract_website_data(
                        url=tool_args.get("url"),
                        extraction_type=tool_args.get("extraction_type", "general"),
                        selectors=tool_args.get("selectors"),
                        take_screenshot=tool_args.get("take_screenshot", True)
                    )
                    # Ensure proper response format
                    result = {
                        "status": "success",
                        "data": extraction_result.get("structured_data", {}),
                        "title": extraction_result.get("title", ""),
                        "content": extraction_result.get("content", ""),
                        "links": extraction_result.get("structured_data", {}).get("links", []),
                        "url": extraction_result.get("url", tool_args.get("url")),
                        "extraction_type": extraction_result.get("extraction_type", "general")
                    }
                else:
                    return self.error_response(f"Unknown tool: {tool_name}", -32601, request_id)
                    
            elif method == "extract_website_data":
                extraction_result = await self.agent.extract_website_data(
                    url=params.get("url"),
                    extraction_type=params.get("extraction_type", "general"),
                    selectors=params.get("selectors"),
                    take_screenshot=params.get("take_screenshot", True)
                )
                # Ensure proper response format
                result = {
                    "status": "success",
                    "data": extraction_result.get("structured_data", {}),
                    "title": extraction_result.get("title", ""),
                    "content": extraction_result.get("content", ""),
                    "links": extraction_result.get("structured_data", {}).get("links", []),
                    "url": extraction_result.get("url", params.get("url")),
                    "extraction_type": extraction_result.get("extraction_type", "general")
                }
            elif method == "extract_stock_data":
                # Mock stock data extraction
                result = {
                    "url": params.get("url", "https://finance.yahoo.com/sectors/technology/semiconductors/"),
                    "stock_data": {
                        "semiconductor_stocks": [
                            {
                                "symbol": "NVDA",
                                "name": "NVIDIA Corporation", 
                                "price": "$875.50",
                                "change": "+12.45",
                                "change_percent": "+1.44%"
                            },
                            {
                                "symbol": "AMD",
                                "name": "Advanced Micro Devices",
                                "price": "$145.75", 
                                "change": "-2.30",
                                "change_percent": "-1.55%"
                            }
                        ]
                    },
                    "timestamp": datetime.now().isoformat()
                }
            elif method == "process_query":
                result = await self.agent.process_query(params.get("query", ""))
            elif method == "query_extractions":
                result = await self.agent.query_extractions(
                    url_pattern=params.get("url_pattern"),
                    extraction_type=params.get("extraction_type"),
                    limit=params.get("limit", 10)
                )
            elif method == "take_screenshot":
                result = {
                    "url": params.get("url"),
                    "screenshot_path": f"data/screenshots/mock_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
                    "message": "Mock screenshot taken"
                }
            else:
                return self.error_response(f"Unknown method: {method}", -32601, request_id)
            
            return self.success_response(result, request_id)
            
        except Exception as e:
            logger.error(f"Error handling MCP request: {e}", exc_info=True)
            return self.error_response(f"Internal error: {str(e)}", -32603, request_id)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "browserbase_agent",
            "port": self.port,
            "agent_ready": self.agent is not None
        })
    
    async def status_check(self, request):
        """Status check endpoint"""
        status = {
            "service": "browserbase_agent",
            "port": self.port,
            "agent_initialized": self.agent is not None,
            "capabilities": [
                "extract_website_data",
                "extract_stock_data", 
                "process_query",
                "query_extractions",
                "take_screenshot"
            ]
        }
        
        if self.agent:
            status.update({
                "session_id": getattr(self.agent, 'session_id', None),
                "tools_count": len(getattr(self.agent, 'tools', [])),
                "extraction_mode": "mock" if not self.agent.mcp_client else "real"
            })
        
        return web.json_response(status)
    
    def success_response(self, result, request_id=None):
        """Create JSON-RPC success response"""
        response_data = {
            "jsonrpc": "2.0",
            "result": result
        }
        if request_id:
            response_data["id"] = request_id
        
        return web.json_response(response_data)
    
    def error_response(self, message, code=-32603, request_id=None):
        """Create JSON-RPC error response"""
        response_data = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        if request_id:
            response_data["id"] = request_id
        
        return web.json_response(response_data)
    
    async def start_server(self):
        """Start the HTTP server"""
        try:
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            site = web.TCPSite(self.runner, 'localhost', self.port)
            await site.start()
            
            logger.info(f"🚀 Browserbase Agent server started on http://localhost:{self.port}")
            logger.info(f"📋 Available endpoints:")
            logger.info(f"   • POST /mcp - Main MCP endpoint")
            logger.info(f"   • GET  /health - Health check")
            logger.info(f"   • GET  /status - Status information")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start server: {e}")
            return False
    
    async def run(self):
        """Run the server"""
        try:
            logger.info(f"🌐 Starting Browserbase Agent Server on port {self.port}")
            
            # Initialize agent
            await self.initialize_agent()
            
            # Create web app
            await self.create_app()
            
            # Start server
            if await self.start_server():
                logger.info("✅ Browserbase Agent ready for requests")
                
                # Register with hub
                await self.register_with_hub()
                
                # Keep running
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("🛑 Shutdown signal received")
            
        except Exception as e:
            logger.error(f"❌ Server error: {e}")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """Clean shutdown"""
        logger.info("🔄 Shutting down Browserbase Agent server...")
        
        if self.agent:
            await self.agent.cleanup()
        
        if self.runner:
            await self.runner.cleanup()
        
        logger.info("✅ Browserbase Agent shutdown complete")

async def main():
    """Main entry point"""
    port = int(os.getenv("BROWSERBASE_AGENT_PORT", 8001))
    
    server = BrowserbaseAgentServer(port=port)
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())
