#!/usr/bin/env python3
"""
Updated Browserbase API Integration
===================================

Fixed integration with the latest Browserbase API authentication
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

class FixedBrowserbaseAgent:
    """Fixed Browserbase agent with updated API authentication"""
    
    def __init__(self, llm):
        self.llm = llm
        self.agent_id = "fixed_browserbase_agent"
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
        # Enhanced extraction targets with real CSS selectors
        self.extraction_targets = {
            'yahoo_finance_semiconductors': {
                'name': 'Yahoo Finance Semiconductors',
                'url': 'https://finance.yahoo.com/screener/predefined/sec-semiconductors',
                'description': 'Real semiconductor stock data from Yahoo Finance',
                'wait_for_selector': 'tbody tr',
                'data_selectors': {
                    'rows': 'tbody tr',
                    'fields': {
                        'symbol': 'td[aria-label*="Symbol"] a',
                        'name': 'td[aria-label*="Name"]',
                        'price': 'td[aria-label*="Price"]',
                        'change': 'td[aria-label*="Change"]',
                        'volume': 'td[aria-label*="Volume"]',
                        'market_cap': 'td[aria-label*="Market Cap"]'
                    }
                }
            },
            'hacker_news': {
                'name': 'Hacker News Top Stories',
                'url': 'https://news.ycombinator.com/',
                'description': 'Real tech news from Hacker News',
                'wait_for_selector': '.athing',
                'data_selectors': {
                    'rows': '.athing',
                    'fields': {
                        'title': '.titleline a',
                        'url': '.titleline a',
                        'points': '.score',
                        'rank': '.rank'
                    }
                }
            }
        }
    
    async def create_browserbase_session_new_api(self) -> Optional[str]:
        """Create Browserbase session using updated API"""
        
        if not self.use_browserbase:
            return None
            
        try:
            # Try the new API endpoint format
            session_data = {
                "projectId": self.browserbase_project_id,
                "browserSettings": {
                    "viewport": {"width": 1920, "height": 1080}
                }
            }
            
            headers = {
                "Authorization": f"Bearer {self.browserbase_api_key}",
                "Content-Type": "application/json"
            }
            
            # Updated API endpoint
            api_url = "https://www.browserbase.com/v1/sessions"
            
            print(f"🌐 Creating Browserbase session...")
            print(f"API URL: {api_url}")
            print(f"Project ID: {self.browserbase_project_id}")
            
            response = requests.post(api_url, headers=headers, json=session_data)
            
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    if "id" in result:
                        session_id = result["id"]
                        print(f"✅ Session created: {session_id}")
                        return session_id
                    else:
                        print(f"⚠️  Session response: {result}")
                        return None
                except json.JSONDecodeError:
                    print(f"⚠️  Could not parse response as JSON: {response.text[:200]}...")
                    return None
            else:
                print(f"❌ Session creation failed: {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                return None
                
        except Exception as e:
            print(f"❌ Error creating session: {e}")
            return None
    
    async def extract_with_fallback_http(self, target_name: str) -> List[Dict[str, Any]]:
        """Fallback to simple HTTP extraction when Browserbase is not working"""
        
        target_config = self.extraction_targets.get(target_name)
        if not target_config:
            print(f"❌ Target {target_name} not found")
            return []
        
        print(f"🌐 Using HTTP fallback for: {target_config['url']}")
        
        try:
            # Use aiohttp for simple HTTP request
            async with aiohttp.ClientSession() as session:
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                async with session.get(target_config['url'], headers=headers) as response:
                    if response.status == 200:
                        html_content = await response.text()
                        print(f"✅ Downloaded {len(html_content)} characters of HTML")
                        
                        # Parse with Claude
                        extracted_data = await self.parse_html_with_claude_simple(html_content, target_config)
                        return extracted_data
                    else:
                        print(f"❌ HTTP request failed: {response.status}")
                        return []
                        
        except Exception as e:
            print(f"❌ HTTP extraction error: {e}")
            return []
    
    async def parse_html_with_claude_simple(self, html_content: str, target_config: Dict) -> List[Dict[str, Any]]:
        """Use Claude to parse HTML and extract structured data"""
        
        # Truncate HTML for Claude processing
        html_sample = html_content[:8000] if len(html_content) > 8000 else html_content
        
        prompt = f"""
        You are an expert web scraper. Extract structured data from this HTML content.
        
        Target: {target_config['name']}
        URL: {target_config['url']}
        Description: {target_config['description']}
        
        HTML Content Sample:
        {html_sample}
        
        Instructions:
        1. Look for tabular data or structured content relevant to {target_config['name']}
        2. Extract real data from the HTML (not simulated)
        3. For financial data: look for stock symbols, prices, changes, volumes
        4. For news data: look for headlines, links, points/scores
        5. Return data as a JSON array of objects
        6. Each object should have meaningful field names
        7. Include source URL and extraction timestamp
        8. Limit to top 10 most relevant items
        
        Return ONLY a valid JSON array format - no other text.
        """
        
        try:
            response = await self.llm.ainvoke(prompt)
            response_text = response.content.strip()
            
            # Try to extract JSON from response
            if response_text.startswith('['):
                extracted_data = json.loads(response_text)
            else:
                # Look for JSON array in the response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                if start_idx != -1 and end_idx != 0:
                    json_text = response_text[start_idx:end_idx]
                    extracted_data = json.loads(json_text)
                else:
                    extracted_data = []
            
            if not isinstance(extracted_data, list):
                extracted_data = [extracted_data] if extracted_data else []
            
            # Add metadata
            for item in extracted_data:
                if isinstance(item, dict):
                    item['extracted_at'] = time.time()
                    item['source'] = target_config['url']
                    item['extraction_method'] = 'http_fallback'
            
            print(f"✅ Extracted {len(extracted_data)} items using HTTP + Claude")
            return extracted_data
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Could not parse Claude response as JSON: {e}")
            print(f"Response was: {response.content[:200]}...")
            return []
        except Exception as e:
            print(f"❌ Claude parsing error: {e}")
            return []
    
    async def extract_data(self, target_name: str) -> List[Dict[str, Any]]:
        """Main extraction method - tries Browserbase first, falls back to HTTP"""
        
        if self.use_browserbase:
            # Try to create Browserbase session
            session_id = await self.create_browserbase_session_new_api()
            
            if session_id:
                print(f"🎯 Would use Browserbase session {session_id} for extraction")
                # For now, fall back to HTTP since session creation is working but extraction needs more work
                return await self.extract_with_fallback_http(target_name)
            else:
                print("⚠️  Browserbase session creation failed, using HTTP fallback")
                return await self.extract_with_fallback_http(target_name)
        else:
            return await self.extract_with_fallback_http(target_name)
    
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
                    "extraction_method": "http_with_claude"
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
                    "extraction_method": "http_with_claude"
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
        """Run complete extraction workflow with HTTP + Claude fallback"""
        print(f"🚀 Starting SMART extraction workflow for: {target_name}")
        
        # Step 1: Extract data
        extracted_data = await self.extract_data(target_name)
        
        if not extracted_data:
            return {
                "workflow_status": "failed",
                "error": "No data extracted",
                "extraction_method": "http_fallback"
            }
        
        print(f"✅ Extracted {len(extracted_data)} items")
        
        # Step 2: Store in database
        db_result = await self.send_to_database_agent(extracted_data, target_name)
        
        # Step 3: Send email notification
        email_result = await self.send_email_notification(extracted_data, target_name)
        
        return {
            "workflow_status": "completed",
            "extracted_items": len(extracted_data),
            "extraction_method": "http_with_claude",
            "database_result": db_result,
            "email_result": email_result,
            "sample_data": extracted_data[:3] if extracted_data else []
        }

# Test the fixed agent
async def test_fixed_browserbase():
    """Test the fixed Browserbase agent with HTTP fallback"""
    print("🌐 Fixed Browserbase Agent - Smart Extraction")
    print("=" * 60)
    
    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.1,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    # Create fixed agent
    agent = FixedBrowserbaseAgent(llm)
    
    # Test extraction
    print("\n🎯 Testing Yahoo Finance extraction...")
    result = await agent.run_extraction_workflow("yahoo_finance_semiconductors")
    
    print("\n🎯 EXTRACTION WORKFLOW RESULTS")
    print("=" * 50)
    print(f"Status: {result.get('workflow_status')}")
    print(f"Method: {result.get('extraction_method')}")
    print(f"Items: {result.get('extracted_items')}")
    print(f"Database: {result.get('database_result', {}).get('status')}")
    print(f"Email: {result.get('email_result', {}).get('status')}")
    
    # Show sample data
    sample_data = result.get('sample_data', [])
    if sample_data:
        print(f"\n📊 Sample Data:")
        for i, item in enumerate(sample_data, 1):
            print(f"  {i}. {json.dumps(item, indent=4)}")
    
    return result

if __name__ == "__main__":
    asyncio.run(test_fixed_browserbase())
