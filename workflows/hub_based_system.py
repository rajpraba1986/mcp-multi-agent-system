#!/usr/bin/env python3
"""
Hub-Based MCP Multi-Agent System
=====================================

This implementation follows proper hub architecture where:
1. All agents register with the MCP Hub
2. Agent discovery happens through the hub
3. A2A communication is mediated by the hub
4. Workflow orchestration uses hub-based discovery

Architecture:
- MCP Hub (Port 5000) - Central registry and discovery
- Agents register their capabilities with the hub
- Coordinator discovers agents through hub and orchestrates workflow
"""

import asyncio
import os
import sys
import time
import subprocess
import signal
import yaml
import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any

# Setup path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv()

class HubClient:
    """Client for communicating with MCP Hub"""
    
    def __init__(self, hub_url: str = "http://localhost:5000"):
        self.hub_url = hub_url
        self._session = None
        
    async def _ensure_session(self):
        """Ensure aiohttp session exists"""
        if self._session is None:
            import aiohttp
            self._session = aiohttp.ClientSession()
    
    async def discover_agents(self, agent_type: str = None, capability: str = None) -> List[Dict]:
        """Discover agents through the hub"""
        await self._ensure_session()
        
        request_data = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "agents/discover",
            "params": {}
        }
        
        if agent_type:
            request_data["params"]["agent_type"] = agent_type
        if capability:
            request_data["params"]["capability"] = capability
            
        try:
            async with self._session.post(f"{self.hub_url}/mcp", json=request_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("result", {}).get("agents", [])
                else:
                    print(f"❌ Hub discovery failed: HTTP {response.status}")
                    return []
        except Exception as e:
            print(f"❌ Hub discovery error: {e}")
            return []
    
    async def call_agent_via_hub(self, agent_id: str, method: str, params: Dict = None) -> Dict:
        """Call agent through hub-mediated communication"""
        await self._ensure_session()
        
        request_data = {
            "jsonrpc": "2.0", 
            "id": str(uuid.uuid4()),
            "method": "agents/call",
            "params": {
                "target_agent_id": agent_id,
                "method": method,
                "params": params or {}
            }
        }
        
        try:
            async with self._session.post(f"{self.hub_url}/mcp", json=request_data) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    if "result" in result:
                        # Handle nested hub response
                        actual_result = result.get("result", {})
                        if isinstance(actual_result, dict) and "result" in actual_result:
                            # Double-nested response from hub
                            return actual_result["result"]
                        else:
                            return actual_result
                    elif "error" in result:
                        return {"status": "error", "message": f"Hub error: {result['error']}"}
                    else:
                        return {"status": "error", "message": f"Unexpected response format: {result}"}
                else:
                    response_text = await response.text()
                    return {"status": "error", "message": f"HTTP {response.status}: {response_text[:100]}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def close(self):
        """Close the session"""
        if self._session:
            await self._session.close()
            self._session = None

class HubBasedWorkflowOrchestrator:
    """Orchestrates workflow using hub-based agent discovery"""
    
    def __init__(self):
        self.project_root = project_root
        self.scraping_config = self._load_scraping_config()
        self.hub_client = HubClient()
        self.processes: List[subprocess.Popen] = []
        
    def _load_scraping_config(self) -> Dict[str, Any]:
        """Load scraping configuration from YAML file."""
        config_path = self.project_root / "config" / "scraping_config.yaml"
        try:
            with open(config_path, 'r') as file:
                config = yaml.safe_load(file)
                print(f"✅ Loaded scraping configuration: {len(config.get('urls_to_scrape', []))} URLs")
                return config
        except Exception as e:
            print(f"⚠️  Failed to load scraping config: {e}")
            return {"urls_to_scrape": [], "email_settings": {}, "database_settings": {}}
    
    def start_agent(self, script_name: str, agent_name: str, wait_time: int = 3) -> bool:
        """Start an agent script"""
        try:
            script_path = self.project_root / script_name
            if not script_path.exists():
                print(f"❌ Script not found: {script_path}")
                return False
                
            print(f"🚀 Starting {agent_name}...")
            process = subprocess.Popen(
                [sys.executable, str(script_path)],
                cwd=str(self.project_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.poll() is None:
                self.processes.append(process)
                print(f"⏳ Waiting {wait_time} seconds for {agent_name} to initialize...")
                time.sleep(wait_time)
                
                if process.poll() is None:
                    print(f"✅ {agent_name} started successfully")
                    return True
                else:
                    stdout, stderr = process.communicate()
                    print(f"❌ {agent_name} crashed during startup")
                    if stderr:
                        print(f"   Error: {stderr[:200]}...")
                    return False
            else:
                print(f"❌ {agent_name} failed to start immediately")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start {agent_name}: {e}")
            return False

    async def start_system(self):
        """Start all agents in the system"""
        print("🌟 Hub-Based MCP Multi-Agent System")
        print("=" * 50)
        
        # Check environment
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if api_key:
            print(f"✅ ANTHROPIC_API_KEY loaded ({len(api_key)} chars)")
        else:
            print("❌ ANTHROPIC_API_KEY not found!")
        
        # Start agents in order
        agents = [
            ("src/hub/mcp_hub.py", "MCP Hub", 8),
            ("src/agents/postgresql_database_agent.py", "PostgreSQL Database Agent", 8),
            ("src/agents/real_email_agent.py", "Real Email Agent", 5),
            ("launchers/browserbase_server.py", "Browserbase MCP Server", 5)
        ]
        
        started_agents = []
        for script, name, wait in agents:
            if self.start_agent(script, name, wait):
                started_agents.append(name)
            else:
                print(f"❌ Failed to start {name}")
                return False
        
        if len(started_agents) == len(agents):
            print(f"\n🎉 ALL {len(agents)} AGENTS STARTED SUCCESSFULLY!")
            print("=" * 50)
            return True
        else:
            print(f"❌ Only {len(started_agents)}/{len(agents)} agents started")
            return False

    async def discover_and_test_agents(self):
        """Discover agents through hub and test connectivity"""
        print(f"\n🔍 Discovering agents through MCP Hub...")
        
        # Wait for agents to register
        await asyncio.sleep(5)
        
        # Discover all agents
        agents = await self.hub_client.discover_agents()
        
        if not agents:
            print("❌ No agents discovered through hub")
            return {}
        
        print(f"✅ Discovered {len(agents)} agents through hub:")
        discovered_agents = {}
        
        for agent in agents:
            agent_id = agent["agent_id"]
            agent_type = agent["agent_type"]
            capabilities = [cap["name"] for cap in agent["capabilities"]]
            
            print(f"   • {agent['agent_name']} ({agent_type})")
            print(f"     ID: {agent_id}")
            print(f"     Capabilities: {', '.join(capabilities)}")
            
            discovered_agents[agent_type] = {
                "agent_id": agent_id,
                "capabilities": capabilities,
                "endpoint": agent["endpoint_url"]
            }
        
        return discovered_agents

    async def run_hub_based_workflow(self):
        """Run extraction workflow using hub-based agent discovery"""
        print(f"\n🚀 Running Hub-Based Extraction Workflow...")
        print("=" * 60)
        
        # Discover agents through hub
        agents = await self.discover_and_test_agents()
        
        if not agents:
            print("❌ Cannot proceed without agent discovery")
            return
        
        # Check required agents
        required_agents = ["browserbase", "database", "communication"]
        missing_agents = [agent for agent in required_agents if agent not in agents]
        
        if missing_agents:
            print(f"❌ Missing required agents: {missing_agents}")
            return
        
        print(f"✅ All required agents discovered through hub")
        
        # Get URLs from scraping configuration
        urls_to_scrape = self.scraping_config.get('urls_to_scrape', [])
        active_urls = [url_config for url_config in urls_to_scrape if url_config.get('active', True)]
        
        if not active_urls:
            print("⚠️  No active URLs found in scraping configuration")
            return
        
        print(f"📋 Processing {len(active_urls)} URLs via hub-mediated A2A communication...")
        
        extraction_results = []
        successful_extractions = 0
        failed_extractions = 0
        
        # Process each URL using hub-mediated communication with rate limiting
        for i, url_config in enumerate(active_urls):
            url = url_config['url']
            name = url_config['name']
            extraction_type = url_config.get('extraction_type', 'general')
            
            # Rate limiting: Add delay between requests to avoid API rate limits
            if i > 0:
                delay_seconds = 3  # 3 second delay between extractions
                print(f"⏳ Rate limiting: Waiting {delay_seconds} seconds before next extraction...")
                await asyncio.sleep(delay_seconds)
            
            print(f"\n🌐 Processing: {name} ({i+1}/{len(active_urls)})")
            print(f"   URL: {url}")
            
            try:
                # 1. Web Extraction via Hub
                browserbase_agent = agents["browserbase"]
                print(f"   📡 Calling browserbase agent via hub...")
                
                # Set appropriate wait times based on domain
                wait_time = 3  # default
                if "finance.yahoo.com" in url:
                    wait_time = 8
                elif "marketbeat.com" in url:
                    wait_time = 6
                elif "news.ycombinator.com" in url:
                    wait_time = 3
                    
                extraction_response = await self.hub_client.call_agent_via_hub(
                    browserbase_agent["agent_id"],
                    "extract_website_data",
                    {
                        "url": url,
                        "extraction_type": extraction_type,
                        "wait_time": wait_time,
                        "extract_links": True
                    }
                )
                
                if extraction_response.get("status") == "success":
                    print(f"   ✅ Web extraction successful")
                    
                    extraction_result = {
                        "url": url,
                        "name": name,
                        "title": extraction_response.get("title", name),
                        "content": extraction_response.get("content", ""),
                        "extracted_data": extraction_response.get("data", {}),
                        "status": "success",
                        "extraction_type": extraction_type
                    }
                    
                    # 2. Database Storage via Hub
                    database_agent = agents["database"]
                    print(f"   📡 Storing data via hub...")
                    
                    storage_response = await self.hub_client.call_agent_via_hub(
                        database_agent["agent_id"],
                        "store_extraction_data",
                        {
                            "data": extraction_result["extracted_data"],
                            "source": url,
                            "timestamp": str(time.time()),
                            "metadata": {
                                "title": extraction_result["title"],
                                "content": extraction_result["content"],
                                "extraction_type": extraction_type,
                                "url": url,
                                "name": name
                            }
                        }
                    )
                    
                    if storage_response.get("status") == "success":
                        print(f"   ✅ Database storage successful")
                        extraction_result["database_result"] = {"status": "success"}
                    else:
                        print(f"   ⚠️  Database storage failed")
                        extraction_result["database_result"] = {"status": "failed"}
                    
                    extraction_results.append(extraction_result)
                    successful_extractions += 1
                    
                else:
                    print(f"   ❌ Web extraction failed")
                    failed_extractions += 1
                    
            except Exception as e:
                print(f"   ❌ Processing error: {str(e)[:50]}...")
                failed_extractions += 1
        
        # 3. Email Notification via Hub
        if extraction_results:
            print(f"\n📧 Sending email notification via hub...")
            
            email_agent = agents["communication"]
            email_response = await self.hub_client.call_agent_via_hub(
                email_agent["agent_id"],
                "send_extraction_notification",
                {
                    "extraction_data": extraction_results,
                    "data_count": len(extraction_results),
                    "extraction_source": "Hub-mediated A2A Communication",
                    "extraction_method": "browserbase_hub",
                    "extraction_summary": f"Hub-mediated extraction: {successful_extractions} successful, {failed_extractions} failed"
                }
            )
            
            if email_response.get("status") == "success":
                print(f"   ✅ Email notification sent via hub")
            else:
                print(f"   ❌ Email notification failed")
        
        # Summary
        print(f"\n🎯 HUB-BASED WORKFLOW RESULTS")
        print("=" * 40)
        print(f"✅ Total Processed: {len(active_urls)}")
        print(f"✅ Successful: {successful_extractions}")
        print(f"❌ Failed: {failed_extractions}")
        print(f"📡 All communication via MCP Hub")
        print(f"🔍 Agent discovery via hub")
        
    async def run(self):
        """Run the complete hub-based system"""
        try:
            # Start all agents
            if not await self.start_system():
                return
                
            # Run hub-based workflow
            await self.run_hub_based_workflow()
            
            # Keep running for observation
            print(f"\n⏳ Keeping system running for 30 seconds...")
            await asyncio.sleep(30)
            
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up resources"""
        print("🧹 Cleaning up processes...")
        await self.hub_client.close()
        
        for process in self.processes:
            try:
                if process.poll() is None:
                    process.terminate()
                    time.sleep(1)
                    if process.poll() is None:
                        process.kill()
            except Exception as e:
                print(f"⚠️ Error cleaning up process: {e}")
        self.processes.clear()

async def main():
    """Main entry point"""
    orchestrator = HubBasedWorkflowOrchestrator()
    
    def signal_handler(sig, frame):
        print(f"\n🛑 Received signal {sig}")
        asyncio.create_task(orchestrator.cleanup())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    await orchestrator.run()

if __name__ == "__main__":
    asyncio.run(main())
