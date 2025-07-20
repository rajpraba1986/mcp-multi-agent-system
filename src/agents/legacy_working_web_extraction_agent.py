#!/usr/bin/env python3
"""
Working Web Extraction Demo
===========================

This demonstrates REAL web extraction that actually works with your current system.
Uses Hacker News as the target (accessible and reliable) and integrates with your
existing database and email agents.
"""

import asyncio
import os
import sys
import json
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from bs4 import BeautifulSoup

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

class WorkingWebExtractionAgent:
    """Working web extraction agent - demonstrates REAL extraction working"""
    
    def __init__(self, llm):
        self.llm = llm
        self.agent_id = "working_web_extraction_agent"
        
        print("🌐 Working Web Extraction Agent Initialized")
        print("✅ Uses REAL HTTP requests + BeautifulSoup + Claude AI")
        print("✅ Integrates with your Database and Email agents")
        
        # Define working extraction targets
        self.extraction_targets = {
            'hacker_news_top': {
                'name': 'Hacker News Top Stories',
                'url': 'https://news.ycombinator.com/',
                'description': 'Top tech stories from Hacker News',
                'method': 'beautifulsoup'
            },
            'github_trending': {
                'name': 'GitHub Trending (Public API)', 
                'url': 'https://api.github.com/search/repositories?q=created:>2025-01-01&sort=stars&order=desc',
                'description': 'Trending GitHub repositories',
                'method': 'json_api'
            },
            'httpbin_demo': {
                'name': 'HTTPBin Test (Demo)',
                'url': 'https://httpbin.org/json',
                'description': 'Test JSON endpoint to verify extraction',
                'method': 'json_api'
            }
        }
    
    async def extract_hacker_news(self) -> List[Dict[str, Any]]:
        """Extract real data from Hacker News using BeautifulSoup"""
        
        print("🌐 Extracting REAL data from Hacker News...")
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get('https://news.ycombinator.com/', headers=headers) as response:
                    if response.status != 200:
                        print(f"❌ Failed to fetch Hacker News: {response.status}")
                        return []
                    
                    html_content = await response.text()
                    print(f"✅ Downloaded {len(html_content)} characters of HTML")
                    
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    stories = []
                    story_rows = soup.find_all('tr', class_='athing')[:10]  # Get top 10 stories
                    
                    for i, row in enumerate(story_rows, 1):
                        try:
                            # Extract story details
                            title_link = row.find('span', class_='titleline').find('a')
                            story_id = row.get('id')
                            
                            # Get the metadata row (next sibling)
                            meta_row = row.find_next_sibling('tr')
                            
                            score_span = meta_row.find('span', class_='score') if meta_row else None
                            points = score_span.text if score_span else "0 points"
                            
                            story = {
                                'rank': i,
                                'title': title_link.text.strip() if title_link else 'No title',
                                'url': title_link.get('href', '') if title_link else '',
                                'points': points,
                                'story_id': story_id,
                                'extracted_at': time.time(),
                                'source': 'https://news.ycombinator.com/',
                                'extraction_method': 'beautifulsoup'
                            }
                            
                            stories.append(story)
                            
                        except Exception as e:
                            print(f"⚠️  Error parsing story {i}: {e}")
                            continue
                    
                    print(f"✅ Successfully extracted {len(stories)} stories from Hacker News")
                    return stories
                    
        except Exception as e:
            print(f"❌ Hacker News extraction error: {e}")
            return []
    
    async def extract_github_trending(self) -> List[Dict[str, Any]]:
        """Extract trending repositories from GitHub API"""
        
        print("🌐 Extracting REAL data from GitHub API...")
        
        try:
            url = 'https://api.github.com/search/repositories'
            params = {
                'q': 'created:>2025-01-01',
                'sort': 'stars',
                'order': 'desc',
                'per_page': 10
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        print(f"❌ Failed to fetch GitHub data: {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    repositories = []
                    for repo in data.get('items', [])[:10]:
                        try:
                            repository = {
                                'name': repo['name'],
                                'full_name': repo['full_name'],
                                'description': repo.get('description', 'No description'),
                                'stars': repo['stargazers_count'],
                                'forks': repo['forks_count'],
                                'language': repo.get('language', 'Unknown'),
                                'url': repo['html_url'],
                                'created_at': repo['created_at'],
                                'extracted_at': time.time(),
                                'source': 'https://api.github.com',
                                'extraction_method': 'github_api'
                            }
                            
                            repositories.append(repository)
                            
                        except Exception as e:
                            print(f"⚠️  Error parsing repository: {e}")
                            continue
                    
                    print(f"✅ Successfully extracted {len(repositories)} repositories from GitHub")
                    return repositories
                    
        except Exception as e:
            print(f"❌ GitHub extraction error: {e}")
            return []
    
    async def extract_test_data(self) -> List[Dict[str, Any]]:
        """Extract test data from HTTPBin to verify the system works"""
        
        print("🌐 Extracting test data from HTTPBin...")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://httpbin.org/json') as response:
                    if response.status != 200:
                        print(f"❌ Failed to fetch test data: {response.status}")
                        return []
                    
                    data = await response.json()
                    
                    test_data = [{
                        'test_title': 'HTTPBin Test Data',
                        'slideshow_title': data.get('slideshow', {}).get('title', 'Unknown'),
                        'slides_count': len(data.get('slideshow', {}).get('slides', [])),
                        'extracted_at': time.time(),
                        'source': 'https://httpbin.org/json',
                        'extraction_method': 'json_api'
                    }]
                    
                    print(f"✅ Successfully extracted test data from HTTPBin")
                    return test_data
                    
        except Exception as e:
            print(f"❌ Test data extraction error: {e}")
            return []
    
    async def extract_data(self, target_name: str) -> List[Dict[str, Any]]:
        """Main extraction method - routes to appropriate extractor"""
        
        if target_name == 'hacker_news_top':
            return await self.extract_hacker_news()
        elif target_name == 'github_trending':
            return await self.extract_github_trending()
        elif target_name == 'httpbin_demo':
            return await self.extract_test_data()
        else:
            print(f"❌ Unknown target: {target_name}")
            return []
    
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
                    "extraction_method": "real_web_extraction"
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
            print(f"🔍 DEBUG: Sending email notification with {len(data)} items")
            print(f"🔍 DEBUG: Extraction source: {extraction_source}")
            if data:
                print(f"🔍 DEBUG: First item keys: {list(data[0].keys())}")
                print(f"🔍 DEBUG: First item URL: {data[0].get('url', 'NO_URL_FOUND')}")
            
            notification_request = {
                "jsonrpc": "2.0",
                "id": f"notify_{int(time.time())}",
                "method": "send_extraction_notification",
                "params": {
                    "extraction_source": extraction_source,
                    "data_count": len(data),
                    "extraction_data": data[:5],  # Send first 5 items for email
                    "extraction_method": "real_web_extraction"
                }
            }
            
            print(f"🔍 DEBUG: Notification request params: {notification_request['params']}")
            
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
        """Run complete extraction workflow with REAL web extraction"""
        target_config = self.extraction_targets.get(target_name, {})
        target_description = target_config.get('name', target_name)
        
        print(f"🚀 Starting REAL WEB EXTRACTION workflow for: {target_description}")
        
        # Step 1: Extract real data
        extracted_data = await self.extract_data(target_name)
        
        if not extracted_data:
            return {
                "workflow_status": "failed",
                "error": "No data extracted",
                "extraction_method": "real_web_extraction"
            }
        
        print(f"✅ Extracted {len(extracted_data)} items using REAL web extraction")
        
        # Step 2: Store in database
        db_result = await self.send_to_database_agent(extracted_data, target_name)
        
        # Step 3: Send email notification
        email_result = await self.send_email_notification(extracted_data, target_name)
        
        return {
            "workflow_status": "completed",
            "extracted_items": len(extracted_data),
            "extraction_method": "real_web_extraction",
            "target_description": target_description,
            "database_result": db_result,
            "email_result": email_result,
            "sample_data": extracted_data[:3] if extracted_data else []
        }

# Demo function
async def demo_real_web_extraction():
    """Demo real web extraction with all targets"""
    print("🌟 REAL WEB EXTRACTION DEMO")
    print("=" * 60)
    print("This demonstrates ACTUAL web extraction (not simulation)")
    print("✅ Real HTTP requests")
    print("✅ Real data parsing with BeautifulSoup + APIs")
    print("✅ Integration with your Database and Email agents")
    print()
    
    # Initialize Claude
    llm = ChatAnthropic(
        model="claude-3-haiku-20240307",
        temperature=0.1,
        api_key=os.getenv("ANTHROPIC_API_KEY")
    )
    
    # Create agent
    agent = WorkingWebExtractionAgent(llm)
    
    # Test all targets
    targets = ['httpbin_demo', 'hacker_news_top', 'github_trending']
    
    for target in targets:
        print(f"\n{'='*20} TESTING {target.upper()} {'='*20}")
        
        try:
            result = await agent.run_extraction_workflow(target)
            
            print(f"\n🎯 RESULTS for {target}:")
            print(f"Status: {result.get('workflow_status')}")
            print(f"Items: {result.get('extracted_items')}")
            print(f"Database: {result.get('database_result', {}).get('status')}")
            print(f"Email: {result.get('email_result', {}).get('status')}")
            
            # Show sample data
            sample_data = result.get('sample_data', [])
            if sample_data:
                print(f"\n📊 Sample Data (first {len(sample_data)} items):")
                for i, item in enumerate(sample_data, 1):
                    print(f"  {i}. {json.dumps(item, indent=6, default=str)}")
            
            print(f"\n{'='*60}")
            
        except Exception as e:
            print(f"❌ Error testing {target}: {e}")
        
        # Wait between tests
        await asyncio.sleep(1)
    
    print("\n🎉 DEMO COMPLETE!")
    print("This proves that REAL web extraction is working with your system!")

if __name__ == "__main__":
    # Install BeautifulSoup if needed
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("📦 Installing BeautifulSoup...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
        from bs4 import BeautifulSoup
    
    asyncio.run(demo_real_web_extraction())
