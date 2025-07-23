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
import uuid
import sqlite3
from datetime import datetime
from pathlib import Path
import base64
from urllib.parse import urlparse
import aiohttp
import aiohttp_cors
from aiohttp import web
from io import BytesIO
from PIL import Image
from playwright.async_api import async_playwright

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import required modules
from langchain_anthropic import ChatAnthropic
load_dotenv(project_root / ".env")

# Browserbase API configuration
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")
BROWSERBASE_ENABLED = os.getenv("BROWSERBASE_ENABLED", "true").lower() == "true"

print(f"🔑 BROWSERBASE_API_KEY loaded: {'✅ Yes' if BROWSERBASE_API_KEY else '❌ No'}")
print(f"🏗️  BROWSERBASE_PROJECT_ID loaded: {'✅ Yes' if BROWSERBASE_PROJECT_ID else '❌ No'}")
print(f"🎛️  BROWSERBASE_ENABLED: {'✅ Yes' if BROWSERBASE_ENABLED else '❌ No (Playwright-only mode)'}")

# Simple LLM mock for testing

# Simple LLM mock for testing
# Real LLM configuration
def create_llm():
    """Create real Anthropic LLM instance"""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is required")
    
    return ChatAnthropic(
        model="claude-3-sonnet-20240229",
        anthropic_api_key=api_key,
        max_tokens=4000,
        temperature=0.1
    )

# Simplified Browserbase Agent for testing
class SimpleBrowserbaseAgent:
    def __init__(self, port=8001):
        self.port = port
        self.session_id = None  # Will be created per request
        
        # Load extraction configuration
        try:
            self.extraction_config = load_extraction_config()
            logger.info(f"✅ Loaded extraction config with {len(self.extraction_config.extraction_types)} extraction types")
        except Exception as e:
            logger.warning(f"⚠️  Failed to load extraction config: {e}, using defaults")
            self.extraction_config = ExtractionConfig()
        
        # Initialize real LLM
        try:
            self.llm = create_llm()
            logger.info("✅ Real Anthropic LLM initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize LLM: {e}")
            # Don't raise exception, agent can work without LLM for web extraction
            self.llm = None
        
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
        """Enhanced website data extraction with configurable extraction types"""
        
        logger.info(f"🌍 Starting extraction for: {url}")
        
        # Resolve extraction type using configuration
        resolved_extraction_type = self._resolve_extraction_type(url, extraction_type)
        logger.info(f"� Using extraction type: '{resolved_extraction_type}' (requested: '{extraction_type}')")
        
        # Get extraction settings from config
        extraction_settings = self._get_extraction_settings(resolved_extraction_type)
        
        # Override take_screenshot from config if not explicitly set
        if take_screenshot is True:  # Only override if default True
            take_screenshot = extraction_settings.get("take_screenshot", True)
        
        # Try to extract real data first
        real_data = await self._extract_real_data(url, resolved_extraction_type, extraction_settings)
        
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
            # Return a fallback result instead of raising exception
            extraction_data = {
                "extraction_id": str(uuid.uuid4()),
                "url": url,
                "title": f"Extraction Failed: {url}",
                "content": f"Failed to extract content from {url}",
                "structured_data": {},
                "screenshot_path": None,
                "extraction_method": "failed",
                "timestamp": time.time(),
                "raw_data": real_data or {"error": "Extraction failed"}
            }
            
        # Note: Storage is handled by PostgreSQL Database Agent via MCP hub
        # No local storage needed - everything goes through the database agent
        
        # Return in format expected by workflow
        if real_data and real_data.get('success'):
            return {
                "status": "success",
                "data": extraction_data,
                "title": extraction_data["title"],
                "content": extraction_data["content"],
                "extraction_id": extraction_data["extraction_id"]
            }
        else:
            return {
                "status": "failed",
                "data": extraction_data,
                "title": extraction_data["title"],
                "content": extraction_data["content"],
                "error": "Real data extraction failed",
                "extraction_id": extraction_data["extraction_id"]
            }

    def _resolve_extraction_type(self, url: str, requested_type: str = "general") -> str:
        """
        Resolve the best extraction type for a URL based on configuration.
        
        Args:
            url: Target URL
            requested_type: Explicitly requested extraction type
            
        Returns:
            str: Resolved extraction type
        """
        try:
            # Parse domain from URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Check if requested type is an alias and resolve to primary type
            if requested_type != "general":
                for type_name, type_config in self.extraction_config.extraction_types.items():
                    if requested_type == type_name:
                        return type_name
                    elif requested_type in (type_config.aliases or []):
                        logger.info(f"🔄 Resolved alias '{requested_type}' to primary type '{type_name}'")
                        return type_name
            
            # If not a recognized type/alias, check if domain has specific config
            domain_type = get_extraction_type_for_domain(domain, self.extraction_config)
            if domain_type != "general" and requested_type == "general":
                logger.info(f"🎯 Auto-detected extraction type '{domain_type}' for domain '{domain}'")
                return domain_type
            
            # Return requested type (could be custom or general)
            return requested_type
            
        except Exception as e:
            logger.warning(f"Failed to resolve extraction type: {e}, using '{requested_type}'")
            return requested_type
    
    def _get_extraction_settings(self, extraction_type: str) -> dict:
        """
        Get extraction settings for a specific type.
        
        Args:
            extraction_type: The extraction type
            
        Returns:
            dict: Extraction settings
        """
        try:
            # Start with default settings
            settings = self.extraction_config.default_extraction.copy()
            
            # Add type-specific settings
            if extraction_type in self.extraction_config.extraction_types:
                type_config = self.extraction_config.extraction_types[extraction_type]
                if type_config.wait_time:
                    settings["wait_for_content"] = type_config.wait_time
            
            # Add general extraction settings
            if "extraction_settings" in self.extraction_config.extraction_settings:
                settings.update(self.extraction_config.extraction_settings)
            
            return settings
            
        except Exception as e:
            logger.warning(f"Failed to get extraction settings: {e}")
            return self.extraction_config.default_extraction

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
    
    async def _extract_real_data(self, url, extraction_type="general", extraction_settings=None):
        """Extract real data from webpage using Browserbase API or Playwright fallback"""
        if extraction_settings is None:
            extraction_settings = self._get_extraction_settings(extraction_type)
        try:
            # Check if Browserbase is disabled via configuration
            if not BROWSERBASE_ENABLED:
                logger.info("🎛️ Browserbase disabled in configuration, using Playwright-only mode")
                return await self._extract_with_playwright(url, extraction_type, extraction_settings)
                
            if not BROWSERBASE_API_KEY or not BROWSERBASE_PROJECT_ID:
                logger.warning("Browserbase API credentials not configured, falling back to local Playwright")
                return await self._extract_with_playwright(url, extraction_type, extraction_settings)
            
            logger.info(f"🌍 Extracting real data from {url} using Browserbase API...")
            
            # Create Browserbase session
            session_data = await self._create_browserbase_session()
            if not session_data:
                logger.error("❌ Failed to create Browserbase session")
                logger.info("🔧 Falling back to local Playwright extraction...")
                return await self._extract_with_playwright(url, extraction_type, extraction_settings)
            
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
            return await self._extract_with_playwright(url, extraction_type, extraction_settings)
    
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
    
    async def _extract_with_playwright(self, url, extraction_type="general", extraction_settings=None):
        """Enhanced extraction using local Playwright with configurable extraction types"""
        if extraction_settings is None:
            extraction_settings = self._get_extraction_settings(extraction_type)
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Use timeout from settings
                timeout = extraction_settings.get("timeout", 30000)
                
                # Navigate to URL with configurable timeout
                try:
                    logger.info(f"📡 Navigating to: {url}")
                    await page.goto(url, wait_until='domcontentloaded', timeout=timeout)
                    logger.info(f"✅ Page loaded successfully: {url}")
                except Exception as e:
                    logger.warning(f"Initial navigation failed, trying with basic timeout: {e}")
                    await page.goto(url, timeout=timeout//2)  # Fallback with reduced timeout
                
                # Use wait time from settings with domain-specific adjustments
                base_wait_time = extraction_settings.get("wait_for_content", 4000)
                
                if 'finance.yahoo.com' in url:
                    wait_time = max(base_wait_time, 8000)  # Yahoo Finance needs more time
                    logger.info("⏳ Waiting for Yahoo Finance content to load...")
                elif 'marketbeat.com' in url:
                    wait_time = max(base_wait_time, 6000)  # MarketBeat also needs time
                    logger.info("⏳ Waiting for MarketBeat content to load...")
                elif 'news.ycombinator.com' in url:
                    wait_time = max(base_wait_time, 3000)  # HN loads faster
                    logger.info("⏳ Waiting for Hacker News content to load...")
                else:
                    wait_time = base_wait_time
                
                await page.wait_for_timeout(wait_time)

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
                
                # Enhanced content extraction based on configuration
                logger.info(f"🔍 Extracting content using '{extraction_type}' extraction type for: {url}")
                
                # Check if extraction type is comprehensive or has comprehensive aliases
                comprehensive_aliases = get_extraction_aliases("comprehensive", self.extraction_config)
                if extraction_type.lower() in [alias.lower() for alias in comprehensive_aliases]:
                    logger.info("🔥 Using COMPREHENSIVE extraction mode - extracting ALL data regardless of domain")
                    extraction_result = await self._extract_generic_content(page, url)
                elif extraction_type == 'financial' or 'finance.yahoo.com' in url:
                    extraction_result = await self._extract_yahoo_finance_content(page, url)
                elif extraction_type == 'competitor_analysis' or 'marketbeat.com' in url:
                    extraction_result = await self._extract_marketbeat_content(page, url)
                elif extraction_type == 'github' or 'github.com' in url:
                    extraction_result = await self._extract_github_content(page, url)
                elif extraction_type == 'news' or 'news.ycombinator.com' in url:
                    extraction_result = await self._extract_hackernews_content(page, url)
                else:
                    extraction_result = await self._extract_generic_content(page, url)
                
                await browser.close()

                # Combine results
                content = extraction_result.get('content', '')
                structured_data = extraction_result.get('structured_data', {})
                links = extraction_result.get('links', [])

                # Return in expected format with enhanced metadata
                return {
                    'success': True,
                    'title': title,
                    'content': content,
                    'links': links,
                    'screenshot_path': str(screenshot_path) if screenshot_path else None,
                    'extraction_method': 'local_playwright_enhanced',
                    'metadata': {
                        'content_length': len(content),
                        'links_count': len(links),
                        'structured_data': structured_data,
                        'extraction_type': extraction_result.get('type', 'general')
                    },
                    'timestamp': time.time()
                }
                
        except Exception as e:
            logger.warning(f"Real data extraction failed for {url}: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _extract_yahoo_finance_content(self, page, url):
        """Extract Yahoo Finance specific content"""
        try:
            # Wait for content to load
            await page.wait_for_timeout(2000)
            
            content_data = await page.evaluate('''
                () => {
                    const data = {
                        content: '',
                        structured_data: {
                            stock_data: {},
                            debug_info: {}
                        },
                        links: [],
                        type: 'financial'
                    };
                    
                    // Debug: Check what elements are available
                    data.structured_data.debug_info.total_elements = document.querySelectorAll('*').length;
                    data.structured_data.debug_info.has_tables = document.querySelectorAll('table').length;
                    data.structured_data.debug_info.has_spans = document.querySelectorAll('span').length;
                    
                    // Get all text content first
                    const bodyText = document.body.innerText || document.body.textContent || '';
                    data.structured_data.debug_info.body_length = bodyText.length;
                    
                    // Look for any price-like patterns in text
                    const pricePattern = /\\$?\\d+\\.\\d{2}/g;
                    const prices = bodyText.match(pricePattern) || [];
                    data.structured_data.stock_data.found_prices = prices.slice(0, 5);
                    
                    // Look for percentage changes
                    const changePattern = /[+-]?\\d+\\.\\d{1,2}%/g;
                    const changes = bodyText.match(changePattern) || [];
                    data.structured_data.stock_data.found_changes = changes.slice(0, 5);
                    
                    // Extract meaningful content from body
                    const lines = bodyText.split('\\n').filter(line => {
                        const clean = line.trim();
                        return clean.length > 10 && 
                               clean.length < 200 &&
                               !clean.toLowerCase().includes('cookie') &&
                               !clean.toLowerCase().includes('privacy') &&
                               (clean.includes('$') || clean.includes('%') || 
                                clean.toLowerCase().includes('stock') ||
                                clean.toLowerCase().includes('price') ||
                                clean.toLowerCase().includes('market') ||
                                /\\d/.test(clean));
                    });
                    
                    data.content = lines.slice(0, 20).join('\\n');
                    
                    // If no meaningful content found, get first 1000 chars
                    if (data.content.length < 50) {
                        data.content = bodyText.substring(0, 1000);
                    }
                    
                    // Extract financial-related links
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    data.links = links.slice(0, 10).map(link => ({
                        href: link.href,
                        text: (link.innerText || link.textContent || '').trim()
                    })).filter(link => link.text.length > 0 && link.text.length < 50);
                    
                    return data;
                }
            ''')
            
            logger.info(f"Yahoo Finance extraction result: content_length={len(content_data.get('content', ''))}, debug_info={content_data.get('structured_data', {}).get('debug_info', {})}")
            
            return content_data
            
        except Exception as e:
            logger.error(f"Yahoo Finance extraction failed: {e}")
            return await self._extract_generic_content(page, url)
    
    async def _extract_github_content(self, page, url):
        """Extract GitHub specific content"""
        try:
            content_data = await page.evaluate('''
                () => {
                    const data = {
                        content: '',
                        structured_data: {
                            repositories: [],
                            languages: [],
                            stats: {}
                        },
                        links: [],
                        type: 'github'
                    };
                    
                    // Extract repository information
                    const repoElements = document.querySelectorAll('[data-testid*="repo"], [itemprop="name"], .repo');
                    data.structured_data.repositories = Array.from(repoElements).slice(0, 10).map(el => el.innerText.trim());
                    
                    // Extract languages
                    const langElements = document.querySelectorAll('[data-testid*="lang"], .language, [aria-label*="language"]');
                    data.structured_data.languages = Array.from(langElements).slice(0, 10).map(el => el.innerText.trim());
                    
                    // Extract user stats
                    const statElements = document.querySelectorAll('.Counter, [data-testid*="stat"]');
                    statElements.forEach(el => {
                        const text = el.innerText.trim();
                        const parent = el.parentElement;
                        if (parent) {
                            const label = parent.innerText.toLowerCase();
                            if (label.includes('repo')) data.structured_data.stats.public_repos = text;
                            if (label.includes('follow')) data.structured_data.stats.followers = text;
                        }
                    });
                    
                    // Clean content
                    const mainContent = document.querySelector('main, [role="main"], .application-main') || document.body;
                    data.content = mainContent.innerText.substring(0, 2000);
                    
                    return data;
                }
            ''')
            
            return content_data
            
        except Exception as e:
            logger.error(f"GitHub extraction failed: {e}")
            return await self._extract_generic_content(page, url)
    
    async def _extract_hackernews_content(self, page, url):
        """Extract Hacker News specific content"""
        try:
            content_data = await page.evaluate('''
                () => {
                    const data = {
                        content: '',
                        structured_data: {
                            top_stories: []
                        },
                        links: [],
                        type: 'news'
                    };
                    
                    // Extract story titles and metadata
                    const storyElements = document.querySelectorAll('.titleline, .storylink, .athing');
                    data.structured_data.top_stories = Array.from(storyElements).slice(0, 15).map((el, index) => {
                        const titleEl = el.querySelector('a, .storylink') || el;
                        const scoreEl = document.querySelector(`[id="${el.id}"] + tr .score`) || 
                                      document.querySelector(`#score_${el.id}`);
                        
                        return {
                            title: titleEl.innerText.trim(),
                            url: titleEl.href || '',
                            points: scoreEl ? scoreEl.innerText : '0 points',
                            position: index + 1
                        };
                    }).filter(story => story.title.length > 0);
                    
                    // Clean content
                    data.content = document.body.innerText.substring(0, 2000);
                    
                    return data;
                }
            ''')
            
            return content_data
            
        except Exception as e:
            logger.error(f"Hacker News extraction failed: {e}")
            return await self._extract_generic_content(page, url)
    
    async def _extract_marketbeat_content(self, page, url):
        """Extract MarketBeat specific content for competitor analysis"""
        try:
            logger.info(f"🏢 Extracting MarketBeat competitor data from: {url}")
            
            content_data = await page.evaluate('''
                () => {
                    const data = {
                        content: '',
                        structured_data: {
                            competitors: [],
                            stock_data: {},
                            financial_metrics: {}
                        },
                        links: [],
                        type: 'competitor_analysis'
                    };
                    
                    // Extract competitor information from tables
                    const tables = document.querySelectorAll('table, .table, [class*="competitor"]');
                    const competitors = [];
                    
                    tables.forEach(table => {
                        const rows = table.querySelectorAll('tr');
                        rows.forEach(row => {
                            const cells = row.querySelectorAll('td, th');
                            if (cells.length >= 2) {
                                const companyCell = cells[0];
                                const company = companyCell.innerText.trim();
                                
                                // Look for stock symbols and company names
                                if (company.length > 2 && company.length < 50 && 
                                    (company.includes('(') || /[A-Z]{2,5}/.test(company))) {
                                    competitors.push({
                                        name: company,
                                        data: Array.from(cells).slice(1).map(cell => cell.innerText.trim())
                                    });
                                }
                            }
                        });
                    });
                    
                    data.structured_data.competitors = competitors.slice(0, 10);
                    
                    // Extract financial data patterns
                    const bodyText = document.body.innerText || '';
                    const pricePattern = /\\$?[\\d,]+\\.?\\d{0,2}/g;
                    const percentPattern = /[+-]?\\d+\\.?\\d{0,2}%/g;
                    
                    const prices = bodyText.match(pricePattern) || [];
                    const percentages = bodyText.match(percentPattern) || [];
                    
                    data.structured_data.stock_data = {
                        found_prices: prices.slice(0, 8),
                        found_percentages: percentages.slice(0, 8)
                    };
                    
                    // Extract meaningful content
                    const lines = bodyText.split('\\n').filter(line => {
                        const clean = line.trim();
                        return clean.length > 10 && clean.length < 200 &&
                               (clean.includes('$') || clean.includes('%') || 
                                clean.toLowerCase().includes('competitor') ||
                                clean.toLowerCase().includes('stock') ||
                                clean.toLowerCase().includes('market') ||
                                /\\d/.test(clean));
                    });
                    
                    data.content = lines.slice(0, 25).join('\\n');
                    
                    // Extract relevant links
                    const links = Array.from(document.querySelectorAll('a[href*="stock"], a[href*="quote"]'));
                    data.links = links.slice(0, 10).map(link => ({
                        href: link.href,
                        text: (link.innerText || link.textContent || '').trim()
                    })).filter(link => link.text.length > 0 && link.text.length < 60);
                    
                    return data;
                }
            ''')
            
            logger.info(f"MarketBeat extraction result: content_length={len(content_data.get('content', ''))}, competitors={len(content_data.get('structured_data', {}).get('competitors', []))}")
            
            return content_data
            
        except Exception as e:
            logger.error(f"MarketBeat extraction failed: {e}")
            return await self._extract_generic_content(page, url)
    
    async def _extract_generic_content(self, page, url):
        """Enhanced generic content extraction for comprehensive data collection"""
        try:
            content_data = await page.evaluate('''
                () => {
                    // Remove script and style elements for cleaner content
                    const scripts = document.querySelectorAll('script, style');
                    scripts.forEach(el => el.remove());
                    
                    // Get ALL content (no character limit)
                    const body = document.body;
                    const fullContent = body ? body.innerText : '';
                    
                    // Extract ALL links (no limit)
                    const links = Array.from(document.querySelectorAll('a[href]'));
                    const linkData = links.map(link => ({
                        href: link.href,
                        text: link.innerText.trim(),
                        title: link.title || ''
                    })).filter(link => link.text.length > 0);
                    
                    // Extract images
                    const images = Array.from(document.querySelectorAll('img[src]'));
                    const imageData = images.map(img => ({
                        src: img.src,
                        alt: img.alt || '',
                        title: img.title || ''
                    }));
                    
                    // Extract headings for structure
                    const headings = Array.from(document.querySelectorAll('h1, h2, h3, h4, h5, h6'));
                    const headingData = headings.map(h => ({
                        level: h.tagName.toLowerCase(),
                        text: h.innerText.trim()
                    }));
                    
                    // Extract forms for interactivity
                    const forms = Array.from(document.querySelectorAll('form'));
                    const formData = forms.map(form => ({
                        action: form.action || '',
                        method: form.method || 'get',
                        inputs: Array.from(form.querySelectorAll('input, select, textarea')).map(input => ({
                            type: input.type || input.tagName.toLowerCase(),
                            name: input.name || '',
                            placeholder: input.placeholder || ''
                        }))
                    }));
                    
                    // Extract tables for structured data
                    const tables = Array.from(document.querySelectorAll('table'));
                    const tableData = tables.map(table => {
                        const headers = Array.from(table.querySelectorAll('th')).map(th => th.innerText.trim());
                        const rows = Array.from(table.querySelectorAll('tr')).map(tr => 
                            Array.from(tr.querySelectorAll('td')).map(td => td.innerText.trim())
                        ).filter(row => row.length > 0);
                        return { headers, rows };
                    });
                    
                    // Extract meta tags
                    const metaTags = Array.from(document.querySelectorAll('meta'));
                    const metaData = {};
                    metaTags.forEach(meta => {
                        if (meta.name) metaData[meta.name] = meta.content;
                        if (meta.property) metaData[meta.property] = meta.content;
                    });
                    
                    return {
                        content: fullContent.trim(),
                        structured_data: {
                            headings: headingData,
                            images: imageData,
                            forms: formData,
                            tables: tableData,
                            meta_tags: metaData,
                            content_stats: {
                                total_characters: fullContent.length,
                                total_links: linkData.length,
                                total_images: imageData.length,
                                total_headings: headingData.length,
                                total_forms: formData.length,
                                total_tables: tableData.length
                            }
                        },
                        links: linkData,
                        type: 'comprehensive_general'
                    };
                }
            ''')
            
            return content_data
            
        except Exception as e:
            logger.error(f"Generic extraction failed: {e}")
            return {
                'content': 'Extraction failed',
                'structured_data': {},
                'links': [],
                'type': 'error'
            }
    
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

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Load config utilities after logger is available
try:
    from src.utils.config import (
        load_extraction_config, 
        get_extraction_type_for_domain, 
        get_extraction_aliases,
        ExtractionConfig
    )
    CONFIG_AVAILABLE = True
    logger.info("✅ Extraction configuration utilities loaded")
except ImportError as e:
    logger.warning(f"⚠️  Could not load config utilities: {e}, using fallbacks")
    CONFIG_AVAILABLE = False
    # Fallback config classes
    class ExtractionConfig:
        def __init__(self):
            self.default_extraction = {"type": "general", "take_screenshot": True, "timeout": 30000, "wait_for_content": 4000}
            self.extraction_types = {}
            self.domain_configs = {}
            self.extraction_settings = {}
    
    def load_extraction_config(): 
        return ExtractionConfig()
    
    def get_extraction_type_for_domain(domain, config):
        return "general"
        
    def get_extraction_aliases(extraction_type, config):
        if extraction_type == "comprehensive":
            return ["comprehensive", "full", "complete", "all"]
        return [extraction_type]

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
                    
                    # Get structured data from the correct location in agent response
                    agent_data = extraction_result.get("data", {})
                    structured_data = agent_data.get("structured_data", {})
                    
                    # If no structured data in agent_data, try to get it from raw_data metadata
                    if not structured_data:
                        raw_data = agent_data.get("raw_data", {})
                        if raw_data and raw_data.get("metadata"):
                            structured_data = raw_data.get("metadata", {}).get("structured_data", {})
                    
                    result = {
                        "status": extraction_result.get("status", "unknown"),
                        "data": structured_data,
                        "title": extraction_result.get("title", ""),
                        "content": extraction_result.get("content", ""),
                        "links": agent_data.get("raw_data", {}).get("links", []),
                        "url": tool_args.get("url"),
                        "extraction_type": agent_data.get("raw_data", {}).get("metadata", {}).get("extraction_type", "general"),
                        "extraction_method": agent_data.get("extraction_method", "unknown"),
                        "screenshot_path": agent_data.get("screenshot_path"),
                        "metadata": agent_data.get("raw_data", {}).get("metadata", {})
                    }
                else:
                    return self.error_response(f"Unknown tool: {tool_name}", -32601, request_id)
                    
            elif method == "extract_website_data":
                try:
                    extraction_result = await self.agent.extract_website_data(
                        url=params.get("url"),
                        extraction_type=params.get("extraction_type", "general"),
                        selectors=params.get("selectors"),
                        take_screenshot=params.get("take_screenshot", True)
                    )
                    
                    # Check if extraction was successful
                    if extraction_result and extraction_result.get("status") == "success":
                        # Get structured data from the correct location in agent response
                        agent_data = extraction_result.get("data", {})
                        structured_data = agent_data.get("structured_data", {})
                        
                        # If no structured data in agent_data, try to get it from raw_data metadata
                        if not structured_data:
                            raw_data = agent_data.get("raw_data", {})
                            if raw_data and raw_data.get("metadata"):
                                structured_data = raw_data.get("metadata", {}).get("structured_data", {})
                        
                        result = {
                            "status": "success",
                            "data": structured_data,
                            "title": extraction_result.get("title", ""),
                            "content": extraction_result.get("content", ""),
                            "links": agent_data.get("raw_data", {}).get("links", []),
                            "url": params.get("url"),
                            "extraction_type": agent_data.get("raw_data", {}).get("metadata", {}).get("extraction_type", "general"),
                            "extraction_method": agent_data.get("extraction_method", "unknown"),
                            "screenshot_path": agent_data.get("screenshot_path"),
                            "metadata": agent_data.get("raw_data", {}).get("metadata", {})
                        }
                    else:
                        # Return error response if extraction failed
                        return self.error_response("Web extraction failed", -1, request_id)
                        
                except Exception as e:
                    logger.error(f"Extract website data error: {e}")
                    return self.error_response(f"Extraction error: {str(e)}", -1, request_id)
            elif method == "process_query":
                result = await self.agent.process_query(params.get("query", ""))
            elif method == "query_extractions":
                result = await self.agent.query_extractions(
                    url_pattern=params.get("url_pattern"),
                    extraction_type=params.get("extraction_type"),
                    limit=params.get("limit", 10)
                )
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
                "extraction_mode": "real" if hasattr(self.agent, 'llm_client') else "unknown"
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
