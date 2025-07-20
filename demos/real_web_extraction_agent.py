#!/usr/bin/env python3
"""
Real Web Extraction Agent - HTTP + BeautifulSoup
===============================================

This agent uses HTTP requests and BeautifulSoup to extract real data from websites.
No complex browser automation needed - just direct HTTP scraping.
"""

import asyncio
import json
import logging
import os
import sys
import sqlite3
import aiohttp
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from fastapi import FastAPI
from aiohttp import web
import uvicorn

# Setup project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

logger = logging.getLogger(__name__)

class RealWebExtractionAgent:
    """Real web extraction using HTTP + BeautifulSoup"""
    
    def __init__(self, port=8001):
        self.port = port
        self.session_id = f"real_extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.db_path = Path("data/real_web_extractions.db")
        self.db_path.parent.mkdir(exist_ok=True)
        self._setup_database()
        
        # HTTP session for requests
        self.http_session = None
        
    def _setup_database(self):
        """Setup SQLite database for storing extractions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS web_extractions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        url TEXT NOT NULL,
                        title TEXT,
                        content TEXT,
                        extracted_data TEXT,
                        extraction_type TEXT DEFAULT 'general',
                        status TEXT DEFAULT 'success',
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
                logger.info("Database initialized for real web extractions")
        except Exception as e:
            logger.error(f"Database setup error: {e}")
    
    async def get_http_session(self):
        """Get or create HTTP session"""
        if not self.http_session:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                enable_cleanup_closed=True
            )
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self.http_session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                }
            )
        return self.http_session
    
    async def extract_website_data(self, url: str, extraction_type: str = "general", max_pages: int = 1) -> Dict[str, Any]:
        """Extract real data from website using HTTP + BeautifulSoup"""
        try:
            logger.info(f"🌐 REAL EXTRACTION: Starting extraction from {url}")
            
            session = await self.get_http_session()
            
            # Fetch the page
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                html = await response.text()
                logger.info(f"✅ Fetched {len(html)} chars from {url}")
            
            # Parse with BeautifulSoup
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract basic page info
            title = soup.find('title')
            title_text = title.get_text().strip() if title else "No title"
            
            # Extract meta description
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            description = meta_desc.get('content', '') if meta_desc else ''
            
            # Extract based on type
            if extraction_type == "news":
                extracted_data = await self._extract_news_data(soup, url)
            elif extraction_type == "api":
                # For JSON APIs, try to parse JSON directly
                try:
                    json_data = json.loads(html)
                    extracted_data = {"json_response": json_data}
                except:
                    extracted_data = {"content": html[:1000]}
            else:
                # General extraction
                extracted_data = await self._extract_general_data(soup, url)
            
            # Prepare result
            result = {
                "extraction_id": None,  # Will be set after DB storage
                "url": url,
                "title": title_text,
                "content": soup.get_text()[:2000],  # First 2000 chars
                "description": description,
                "structured_data": extracted_data,
                "extraction_type": extraction_type,
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            }
            
            # Store in database
            extraction_id = await self._store_extraction(result)
            result["extraction_id"] = extraction_id
            
            logger.info(f"✅ REAL EXTRACTION COMPLETE: {len(extracted_data.get('headlines', []))} headlines, {len(extracted_data.get('links', []))} links")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Real extraction failed for {url}: {e}")
            
            # Return error result
            error_result = {
                "extraction_id": None,
                "url": url,
                "title": f"Extraction Error: {url}",
                "content": f"Failed to extract: {str(e)}",
                "structured_data": {"error": str(e)},
                "extraction_type": extraction_type,
                "timestamp": datetime.now().isoformat(),
                "status": "error"
            }
            
            # Store error in DB too
            await self._store_extraction(error_result)
            return error_result
    
    async def _extract_news_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract news-specific data"""
        headlines = []
        links = []
        
        # Common news headline selectors
        headline_selectors = [
            'h1', 'h2', 'h3',
            '.headline', '.title', '.story-title',
            '[class*="headline"]', '[class*="title"]',
            'article h1', 'article h2', 'article h3'
        ]
        
        for selector in headline_selectors:
            elements = soup.select(selector)
            for elem in elements[:10]:  # Limit to 10 per selector
                text = elem.get_text().strip()
                if text and len(text) > 10:  # Filter out short/empty text
                    headlines.append(text)
                    
                    # Try to find associated link
                    link_elem = elem.find('a') or elem.find_parent('a')
                    if link_elem and link_elem.get('href'):
                        full_link = urljoin(url, link_elem['href'])
                        links.append(full_link)
        
        # Remove duplicates while preserving order
        headlines = list(dict.fromkeys(headlines))
        links = list(dict.fromkeys(links))
        
        return {
            "headlines": headlines[:20],  # Top 20 headlines
            "links": links[:20],
            "article_count": len(headlines),
            "extraction_method": "news-optimized"
        }
    
    async def _extract_general_data(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """Extract general website data"""
        # Get all text content
        text_content = soup.get_text()
        
        # Find all links
        links = []
        for link in soup.find_all('a', href=True):
            full_link = urljoin(url, link['href'])
            link_text = link.get_text().strip()
            if link_text and len(link_text) < 100:
                links.append({
                    "url": full_link,
                    "text": link_text
                })
        
        # Find headings
        headings = []
        for heading in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            text = heading.get_text().strip()
            if text:
                headings.append(text)
        
        # Basic stats
        return {
            "headings": headings[:15],
            "links": links[:20],
            "text_length": len(text_content),
            "word_count": len(text_content.split()),
            "paragraph_count": len(soup.find_all('p')),
            "image_count": len(soup.find_all('img')),
            "extraction_method": "general-scraping"
        }
    
    async def _store_extraction(self, result: Dict[str, Any]) -> int:
        """Store extraction result in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO web_extractions (url, title, content, extracted_data, extraction_type, status, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    result["url"],
                    result["title"],
                    result["content"],
                    json.dumps(result["structured_data"]),
                    result["extraction_type"],
                    result["status"],
                    json.dumps({"session_id": self.session_id})
                ))
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Failed to store extraction: {e}")
            return 0
    
    async def handle_mcp_request(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP requests"""
        try:
            method = data.get("method")
            params = data.get("params", {})
            request_id = data.get("id")
            
            if method == "extract_web_data":
                result = await self.extract_website_data(
                    url=params.get("url"),
                    extraction_type=params.get("extraction_type", "general"),
                    max_pages=params.get("max_pages", 1)
                )
                
                return {
                    "jsonrpc": "2.0",
                    "result": result,
                    "id": request_id
                }
            
            elif method == "query_extractions":
                # Simple query implementation
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT * FROM web_extractions ORDER BY created_at DESC LIMIT 10")
                    rows = cursor.fetchall()
                
                extractions = []
                for row in rows:
                    extractions.append({
                        "id": row[0],
                        "url": row[1], 
                        "title": row[2],
                        "extraction_type": row[5],
                        "status": row[6],
                        "created_at": row[8]
                    })
                
                return {
                    "jsonrpc": "2.0",
                    "result": {"extractions": extractions},
                    "id": request_id
                }
            
            else:
                return {
                    "jsonrpc": "2.0",
                    "error": {"code": -1, "message": f"Unknown method: {method}"},
                    "id": request_id
                }
                
        except Exception as e:
            logger.error(f"MCP request error: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {"code": -1, "message": str(e)},
                "id": data.get("id")
            }
    
    async def cleanup(self):
        """Clean up resources"""
        if self.http_session:
            await self.http_session.close()

# Web server setup
class RealWebExtractionServer:
    def __init__(self):
        self.agent = RealWebExtractionAgent()
        
    async def handle_mcp_request(self, request):
        """Handle MCP requests via HTTP"""
        try:
            data = await request.json()
            result = await self.agent.handle_mcp_request(data)
            return web.json_response(result)
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "error": {"code": -1, "message": str(e)},
                "id": None
            }
            return web.json_response(error_response)
    
    async def health_check(self, request):
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "service": "real_web_extraction",
            "extraction_mode": "real_http_scraping",
            "session_id": self.agent.session_id
        })
    
    async def start_server(self):
        """Start the web server"""
        app = web.Application()
        app.router.add_post('/mcp/request', self.handle_mcp_request)
        app.router.add_get('/health', self.health_check)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', 8001)
        
        logger.info(f"🌐 Starting Real Web Extraction Server on port 8001")
        logger.info("🔥 REAL HTTP + BeautifulSoup extraction ready!")
        
        await site.start()
        return runner

async def main():
    """Main server function"""
    logging.basicConfig(level=logging.INFO)
    
    server = RealWebExtractionServer()
    runner = await server.start_server()
    
    try:
        logger.info("✅ Real Web Extraction Agent ready for requests")
        logger.info("🌐 Try: POST http://localhost:8001/mcp/request")
        logger.info("📊 Example: {\"jsonrpc\": \"2.0\", \"method\": \"extract_web_data\", \"params\": {\"url\": \"https://news.ycombinator.com\"}, \"id\": 1}")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down real web extraction server")
    finally:
        await server.agent.cleanup()
        await runner.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
