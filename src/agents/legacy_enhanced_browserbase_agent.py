#!/usr/bin/env python3
"""
Enhanced Browserbase Extraction Agent
====================================

Real web extraction using Browserbase headless browser with the current working system.
This replaces the simulated data with actual live web scraping.
"""

import asyncio
import os
import sys
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml

# Setup path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Core imports
from langchain_anthropic import ChatAnthropic
import aiohttp
import requests

class EnhancedBrowserbaseAgent:
    """Enhanced Browserbase agent with real web extraction capabilities"""
    
    def __init__(self, llm):
        self.llm = llm
        self.agent_id = "enhanced_browserbase_agent"
        self.extraction_targets = {}
        
        # Browserbase configuration
        self.browserbase_api_key = os.getenv("BROWSERBASE_API_KEY")
        self.browserbase_project_id = os.getenv("BROWSERBASE_PROJECT_ID")
        
        if not self.browserbase_api_key:
            print("⚠️  Warning: BROWSERBASE_API_KEY not found, falling back to simulation")
            self.use_browserbase = False
        else:
            self.use_browserbase = True
            print(f"✅ Browserbase configured with project: {self.browserbase_project_id}")
        
        self.load_extraction_config()
    
    def load_extraction_config(self):
        """Load extraction targets with real selectors for Browserbase"""
        try:
            config_path = project_root / "config" / "extraction_targets.yaml"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    if 'extraction_targets' in config_data:
                        self.extraction_targets = config_data['extraction_targets']
                    else:
                        self.extraction_targets = config_data
        except Exception as e:
            print(f"⚠️  Could not load extraction config: {e}")
            
        # Enhanced extraction targets with real CSS selectors
        self.extraction_targets.update({
            'yahoo_finance_semiconductors': {
                'name': 'Yahoo Finance Semiconductors',
                'url': 'https://finance.yahoo.com/screener/predefined/sec-semiconductors',
                'description': 'Real semiconductor stock data from Yahoo Finance',
                'browserbase_selectors': {
                    'stock_rows': 'tbody tr',
                    'symbol': 'td[aria-label="Symbol"] a',
                    'name': 'td[aria-label="Name"]',
                    'price': 'td[aria-label="Price (Intraday)"]',
                    'change': 'td[aria-label="Change"]',
                    'percent_change': 'td[aria-label="% Change"]',
                    'volume': 'td[aria-label="Volume"]',
                    'market_cap': 'td[aria-label="Market Cap"]'
                },
                'wait_for': 'tbody tr',  # Wait for table to load
                'scroll_to_load': True
            },
            'coinmarketcap_top_cryptos': {
                'name': 'CoinMarketCap Top Cryptocurrencies',
                'url': 'https://coinmarketcap.com/',
                'description': 'Real cryptocurrency data from CoinMarketCap',
                'browserbase_selectors': {
                    'crypto_rows': 'tbody tr',
                    'name': '.coin-item-name',
                    'symbol': '.coin-item-symbol',
                    'price': '.price',
                    'change_24h': '.percent-change',
                    'market_cap': '.market-cap',
                    'volume': '.volume'
                },
                'wait_for': 'tbody tr',
                'scroll_to_load': True
            },
            'hacker_news': {
                'name': 'Hacker News Top Stories',
                'url': 'https://news.ycombinator.com/',
                'description': 'Real tech news from Hacker News',
                'browserbase_selectors': {
                    'story_rows': '.athing',
                    'title': '.titleline a',
                    'url': '.titleline a',
                    'points': '.score',
                    'comments': '.subline a:last-child'
                },
                'wait_for': '.athing'
            }
        })
    
    async def extract_with_browserbase(self, target_name: str) -> List[Dict[str, Any]]:
        """Extract data using real Browserbase browser automation"""
        
        if not self.use_browserbase:
            print("❌ Browserbase not configured, cannot extract real data")
            return []
            
        target_config = self.extraction_targets.get(target_name)
        if not target_config:
            print(f"❌ Target {target_name} not found in configuration")
            return []
        
        print(f"🌐 Extracting real data from: {target_config['url']}")
        
        try:
            # Create Browserbase session
            session_response = requests.post(
                "https://www.browserbase.com/v1/sessions",
                headers={
                    "Authorization": f"Bearer {self.browserbase_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "projectId": self.browserbase_project_id,
                    "width": 1920,
                    "height": 1080
                }
            )
            
            if session_response.status_code != 201:
                print(f"❌ Failed to create Browserbase session: {session_response.status_code}")
                return []
            
            session_data = session_response.json()
            session_id = session_data["id"]
            
            print(f"✅ Created Browserbase session: {session_id}")
            
            # Navigate to the target URL
            navigate_response = requests.post(
                f"https://www.browserbase.com/v1/sessions/{session_id}/actions",
                headers={
                    "Authorization": f"Bearer {self.browserbase_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "type": "navigate",
                    "url": target_config["url"]
                }
            )
            
            if navigate_response.status_code != 200:
                print(f"❌ Failed to navigate: {navigate_response.status_code}")
                return []
            
            print(f"🔗 Navigated to: {target_config['url']}")
            
            # Wait for content to load
            if target_config.get('wait_for'):
                time.sleep(3)  # Give time for JavaScript to load
            
            # Get page content
            content_response = requests.get(
                f"https://www.browserbase.com/v1/sessions/{session_id}/content",
                headers={"Authorization": f"Bearer {self.browserbase_api_key}"}
            )
            
            if content_response.status_code != 200:
                print(f"❌ Failed to get page content: {content_response.status_code}")
                return []
            
            page_html = content_response.text
            
            # Parse the HTML with the configured selectors
            extracted_data = await self.parse_html_with_claude(page_html, target_config)
            
            print(f"✅ Extracted {len(extracted_data)} items using real browser")
            
            # Clean up session
            requests.delete(
                f"https://www.browserbase.com/v1/sessions/{session_id}",
                headers={"Authorization": f"Bearer {self.browserbase_api_key}"}
            )
            
            return extracted_data
            
        except Exception as e:
            print(f"❌ Browserbase extraction error: {e}")
            return []
    
    async def parse_html_with_claude(self, html_content: str, target_config: Dict) -> List[Dict[str, Any]]:
        """Use Claude AI to parse HTML content with the configured selectors"""
        
        selectors = target_config.get('browserbase_selectors', {})
        
        prompt = f"""
        You are an expert web scraper. Extract structured data from this HTML content using the provided CSS selectors.
        
        Target: {target_config['name']}
        URL: {target_config['url']}
        
        CSS Selectors to use:
        {json.dumps(selectors, indent=2)}
        
        HTML Content (truncated for analysis):
        {html_content[:5000]}...
        
        Instructions:
        1. Use the CSS selectors to find the relevant data
        2. Extract real data from the HTML (not simulated)
        3. Return data as a JSON array of objects
        4. Include timestamp and source information
        5. Handle any missing fields gracefully
        
        Return only valid JSON array format.
        """
        
        response = await self.llm.ainvoke(prompt)
        
        try:
            extracted_data = json.loads(response.content)
            if not isinstance(extracted_data, list):
                if isinstance(extracted_data, dict) and 'data' in extracted_data:
                    extracted_data = extracted_data['data']
                else:
                    extracted_data = [extracted_data]
            
            # Add metadata
            for item in extracted_data:
                item['extracted_at'] = time.time()
                item['source'] = target_config['url']
                item['extraction_method'] = 'browserbase'
            
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Could not parse Claude response as JSON: {e}")
            return []
    
    async def extract_data(self, target_name: str) -> List[Dict[str, Any]]:
        """Main extraction method - uses Browserbase if available, falls back to simulation"""
        
        if self.use_browserbase:
            return await self.extract_with_browserbase(target_name)
        else:
            # Fallback to simulation (current behavior)
            print("⚠️  Using simulated data - configure Browserbase for real extraction")
            return await self.simulate_extraction(target_name)
    
    async def simulate_extraction(self, target_name: str) -> List[Dict[str, Any]]:
        """Fallback simulation method (current implementation)"""
        target_config = self.extraction_targets.get(target_name, {})
        
        # Current simulation logic (unchanged)
        prompt = f"""
        You are a web scraping agent. Simulate extracting data from {target_config.get('name', target_name)} 
        at URL: {target_config.get('url', 'unknown')}
        
        Create realistic sample data for financial/tech content.
        Return the data in JSON format with an array of extracted items.
        Make it realistic and current.
        """
        
        response = await self.llm.ainvoke(prompt)
        
        try:
            extracted_data = json.loads(response.content)
            if not isinstance(extracted_data, list):
                extracted_data = [
                    {
                        "symbol": "NVDA",
                        "company": "NVIDIA Corporation", 
                        "price": 875.50,
                        "change": "+12.30",
                        "volume": "45.2M",
                        "extracted_at": time.time(),
                        "source": "simulated"
                    }
                ]
        except json.JSONDecodeError:
            extracted_data = [{"simulated": True, "extracted_at": time.time()}]
        
        return extracted_data
    
    # ... (rest of the methods remain the same as current implementation)
    async def send_to_database_agent(self, data: List[Dict[str, Any]], extraction_source: str) -> Dict[str, Any]:
        """Send extracted data to the database agent via A2A communication"""
        try:
            storage_request = {
                "jsonrpc": "2.0",
                "id": f"store_{int(time.time())}",
                "method": "store_extraction_data",
                "params": {
                    "source": extraction_source,
                    "data": data,
                    "extraction_method": "browserbase" if self.use_browserbase else "simulated"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                db_agent_url = "http://localhost:8002/mcp/request"
                async with session.post(db_agent_url, json=storage_request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            print(f"✅ Data successfully stored via Database Agent")
                            return {"status": "success", "storage_result": result["result"]}
                        else:
                            print(f"⚠️  Database Agent returned error: {result.get('error', 'Unknown error')}")
                            return {"status": "error", "error": result.get("error", "Unknown error")}
                    else:
                        print(f"❌ Failed to contact Database Agent: HTTP {response.status}")
                        return {"status": "error", "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ Error sending data to Database Agent: {e}")
            return {"status": "error", "error": str(e)}
    
    async def send_email_notification(self, data: List[Dict[str, Any]], extraction_source: str) -> Dict[str, Any]:
        """Send email notification via Email Agent"""
        try:
            notification_request = {
                "jsonrpc": "2.0",
                "id": f"notify_{int(time.time())}",
                "method": "send_extraction_notification",
                "params": {
                    "extraction_source": extraction_source,
                    "data_count": len(data),
                    "extraction_data": data[:5],  # Send first 5 items for email
                    "extraction_method": "browserbase" if self.use_browserbase else "simulated"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                email_agent_url = "http://localhost:8003/mcp/request"
                async with session.post(email_agent_url, json=notification_request, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            print(f"✅ Email notification sent successfully")
                            return {"status": "success", "notification_result": result["result"]}
                        else:
                            print(f"⚠️  Email Agent returned error: {result.get('error', 'Unknown error')}")
                            return {"status": "error", "error": result.get("error", "Unknown error")}
                    else:
                        print(f"❌ Failed to contact Email Agent: HTTP {response.status}")
                        return {"status": "error", "error": f"HTTP {response.status}"}
        
        except Exception as e:
            print(f"❌ Error sending email notification: {e}")
            return {"status": "error", "error": str(e)}
    
    async def run_extraction_workflow(self, target_name: str) -> Dict[str, Any]:
        """Run complete extraction workflow with real Browserbase"""
        print(f"🚀 Starting {'REAL' if self.use_browserbase else 'SIMULATED'} extraction workflow for: {target_name}")
        
        # Step 1: Extract data (real or simulated)
        extracted_data = await self.extract_data(target_name)
        
        if not extracted_data:
            return {
                "workflow_status": "failed",
                "error": "No data extracted",
                "extraction_method": "browserbase" if self.use_browserbase else "simulated"
            }
        
        print(f"✅ Extracted {len(extracted_data)} items")
        
        # Step 2: Store in database
        db_result = await self.send_to_database_agent(extracted_data, target_name)
        
        # Step 3: Send email notification
        email_result = await self.send_email_notification(extracted_data, target_name)
        
        return {
            "workflow_status": "completed",
            "extracted_items": len(extracted_data),
            "extraction_method": "browserbase" if self.use_browserbase else "simulated",
            "database_result": db_result,
            "email_result": email_result,
            "sample_data": extracted_data[:3] if extracted_data else []
        }

# Test the enhanced agent
async def test_enhanced_browserbase():
    """Test the enhanced Browserbase agent"""
    print("🌐 Enhanced Browserbase Agent - REAL Web Extraction")
    print("=" * 60)
    
    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.1,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    # Create enhanced agent
    agent = EnhancedBrowserbaseAgent(llm)
    
    # Test extraction
    result = await agent.run_extraction_workflow("yahoo_finance_semiconductors")
    
    print("\n🎯 EXTRACTION WORKFLOW RESULTS")
    print("=" * 50)
    print(f"Status: {result.get('workflow_status')}")
    print(f"Method: {result.get('extraction_method')}")
    print(f"Items: {result.get('extracted_items')}")
    print(f"Database: {result.get('database_result', {}).get('status')}")
    print(f"Email: {result.get('email_result', {}).get('status')}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_enhanced_browserbase())
