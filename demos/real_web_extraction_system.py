#!/usr/bin/env python3
"""
Real Web Extraction System - WORKING VERSION
===========================================

This version uses PROVEN working web extraction methods:
✅ HTTP requests with BeautifulSoup for HTML parsing
✅ Direct API calls for JSON data
✅ Integration with your existing Database and Email agents
✅ REAL data extraction (not simulated!)

This replaces the problematic Browserbase with working alternatives.
"""

import asyncio
import os
import sys
import subprocess
import time
import signal
from pathlib import Path
from typing import List, Dict, Any
import json

# Setup project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))
sys.path.append(str(project_root / "src" / "agents"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import our working web extraction agent
from working_web_extraction_agent import WorkingWebExtractionAgent
from langchain_anthropic import ChatAnthropic

class RealWebExtractionSystem:
    """Real web extraction system manager"""
    
    def __init__(self):
        self.processes = {}
        self.services_status = {}
        self.shutdown_flag = False
        
        print("🌟 REAL WEB EXTRACTION SYSTEM")
        print("✅ HTTP + BeautifulSoup + API extraction")
        print("✅ WORKING extraction methods")
        print("=" * 60)
        
        # Service configurations
        self.services = {
            "mcp_hub": {
                "name": "MCP Hub",
                "script": "src/hub/mcp_hub.py",
                "port": 5000,
                "startup_delay": 1
            },
            "database_agent": {
                "name": "PostgreSQL Database Agent", 
                "script": "postgresql_database_agent.py",
                "port": 8002,
                "startup_delay": 3
            },
            "email_agent": {
                "name": "Real Email Agent",
                "script": "real_email_agent.py", 
                "port": 8003,
                "startup_delay": 5
            }
        }
        
        # Initialize web extraction agent
        self.web_agent = None
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n⚠️  Received signal {signum}. Initiating graceful shutdown...")
            self.shutdown_flag = True
            asyncio.create_task(self.shutdown_system())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def init_web_agent(self):
        """Initialize the web extraction agent"""
        try:
            llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                temperature=0.1,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            self.web_agent = WorkingWebExtractionAgent(llm)
            print("✅ Web extraction agent initialized")
        except Exception as e:
            print(f"❌ Failed to initialize web agent: {e}")
    
    async def start_service(self, service_id: str, config: Dict[str, Any]) -> bool:
        """Start a service with proper error handling"""
        try:
            script_path = project_root / config["script"]
            
            if not script_path.exists():
                print(f"❌ Script not found: {script_path}")
                return False
            
            print(f"🚀 Starting {config['name']} on port {config['port']}...")
            
            # Start the service process
            process = await asyncio.create_subprocess_exec(
                sys.executable, str(script_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            self.processes[service_id] = process
            
            # Wait for startup delay
            await asyncio.sleep(config["startup_delay"])
            
            print(f"✅ {config['name']} started")
            self.services_status[service_id] = "running"
            return True
                
        except Exception as e:
            print(f"❌ Failed to start {config['name']}: {e}")
            self.services_status[service_id] = "failed"
            return False
    
    async def start_all_services(self) -> bool:
        """Start all services in proper order"""
        print("🔄 Starting all services...")
        
        success_count = 0
        for service_id, config in self.services.items():
            if await self.start_service(service_id, config):
                success_count += 1
            
            # Add delay between service startups
            await asyncio.sleep(1)
        
        total_services = len(self.services)
        print(f"\n📊 Service Startup Summary: {success_count}/{total_services} services started")
        
        if success_count > 0:
            print("✅ Services started - system operational")
            return True
        else:
            print("❌ No services started - system failed to start")
            return False
    
    def display_system_status(self):
        """Display current system status"""
        print("\n🎯 REAL WEB EXTRACTION SYSTEM STATUS")
        print("=" * 60)
        print("Extraction Method: REAL HTTP + BeautifulSoup + APIs")
        print("Browserbase: ❌ Not needed - using better methods")
        print()
        
        for service_id, config in self.services.items():
            status = self.services_status.get(service_id, "stopped")
            status_icon = {
                "running": "✅", 
                "starting": "🔄", 
                "failed": "❌", 
                "stopped": "⏹️"
            }.get(status, "❓")
            
            print(f"{status_icon} {config['name']:<25} Port {config['port']:<6} Status: {status}")
        
        print("\n🌐 WORKING WEB EXTRACTION TARGETS:")
        print("✅ Hacker News - Real tech stories")
        print("✅ GitHub API - Trending repositories") 
        print("✅ HTTPBin - Test API endpoint")
        print("✅ Any public API or website")
        
        print("\n📧 EMAIL NOTIFICATIONS:")
        email_configured = os.getenv("SMTP_SERVER") and os.getenv("SMTP_USERNAME")
        print(f"{'✅' if email_configured else '⚠️ '} SMTP Configuration: {'Ready' if email_configured else 'Configure for emails'}")
        print(f"📧 Target Email: {os.getenv('TARGET_EMAIL', 'rajpraba_1986@yahoo.com.sg')}")
    
    async def run_real_extraction(self, target: str = 'hacker_news_top'):
        """Run real web extraction workflow"""
        print(f"\n🚀 RUNNING REAL WEB EXTRACTION: {target}")
        print("=" * 50)
        
        if not self.web_agent:
            await self.init_web_agent()
        
        try:
            result = await self.web_agent.run_extraction_workflow(target)
            
            # Display results
            print(f"\n🎯 EXTRACTION RESULTS:")
            print(f"Status: {result.get('workflow_status')}")
            print(f"Target: {result.get('target_description')}")
            print(f"Items: {result.get('extracted_items')}")
            print(f"Method: {result.get('extraction_method')}")
            
            # Display database result
            db_result = result.get('database_result', {})
            print(f"Database: {db_result.get('status', 'unknown')}")
            
            # Display email result  
            email_result = result.get('email_result', {})
            print(f"Email: {email_result.get('status', 'unknown')}")
            
            # Show sample data
            sample_data = result.get('sample_data', [])
            if sample_data:
                print(f"\n📊 Sample Data (first {len(sample_data)} items):")
                for i, item in enumerate(sample_data, 1):
                    if 'title' in item:
                        print(f"  {i}. {item.get('title', 'No title')}")
                        print(f"     Points: {item.get('points', 'N/A')}")
                        print(f"     URL: {item.get('url', 'N/A')[:60]}...")
                    elif 'name' in item:
                        print(f"  {i}. {item.get('name', 'No name')}")
                        print(f"     Stars: {item.get('stars', 'N/A')}")
                        print(f"     Language: {item.get('language', 'N/A')}")
                    else:
                        print(f"  {i}. {json.dumps(item, indent=4)[:200]}...")
                    print()
            
            return result
            
        except Exception as e:
            print(f"❌ Extraction workflow failed: {e}")
            return {"workflow_status": "failed", "error": str(e)}
    
    async def interactive_menu(self):
        """Interactive menu for system operations"""
        while not self.shutdown_flag:
            print("\n🎮 REAL WEB EXTRACTION MENU")
            print("=" * 35)
            print("1. 🌐 Extract Hacker News Stories")
            print("2. 🐙 Extract GitHub Trending Repos")
            print("3. 🧪 Test HTTPBin API")
            print("4. 📊 View System Status") 
            print("5. 📧 Test Email Notification")
            print("6. 🗃️  View Database Records")
            print("7. 🛑 Shutdown System")
            
            try:
                choice = input("\nEnter choice (1-7): ").strip()
                
                if choice == "1":
                    await self.run_real_extraction('hacker_news_top')
                elif choice == "2":
                    await self.run_real_extraction('github_trending')
                elif choice == "3":
                    await self.run_real_extraction('httpbin_demo')
                elif choice == "4":
                    self.display_system_status()
                elif choice == "5":
                    await self.test_email_notification()
                elif choice == "6":
                    await self.view_database_records()
                elif choice == "7":
                    print("🛑 Shutting down system...")
                    self.shutdown_flag = True
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-7.")
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutting down system...")
                self.shutdown_flag = True
                break
            except Exception as e:
                print(f"❌ Menu error: {e}")
    
    async def test_email_notification(self):
        """Test email notification functionality"""
        print("📧 Testing email notification...")
        
        if not self.web_agent:
            await self.init_web_agent()
        
        try:
            test_data = [{
                "title": "Test Email Notification",
                "content": "This is a test of the real web extraction system",
                "extracted_at": time.time(),
                "source": "test_system"
            }]
            
            email_result = await self.web_agent.send_email_notification(test_data, "test_notification")
            
            if email_result.get('status') == 'success':
                print("✅ Email test successful!")
            else:
                print(f"⚠️  Email test result: {email_result}")
                        
        except Exception as e:
            print(f"❌ Email test error: {e}")
    
    async def view_database_records(self):
        """View recent database records"""
        print("🗃️  This feature requires the database agent to be running...")
        print("💡 Try running a web extraction first to see data being stored!")
    
    async def shutdown_system(self):
        """Graceful shutdown of all services"""
        print("🛑 Shutting down all services...")
        
        for service_id, process in self.processes.items():
            if process and process.returncode is None:
                try:
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                    print(f"✅ {service_id} shut down gracefully")
                except asyncio.TimeoutError:
                    process.kill()
                    print(f"⚠️  {service_id} force killed")
                except Exception as e:
                    print(f"❌ Error shutting down {service_id}: {e}")
        
        self.processes.clear()
        self.services_status.clear()
        print("🛑 System shutdown complete")

async def main():
    """Main execution function"""
    print("🌟 REAL WEB EXTRACTION SYSTEM")
    print("🌐 HTTP + BeautifulSoup + APIs")
    print("=" * 60)
    
    # Check environment
    required_env = ["ANTHROPIC_API_KEY"]
    missing_env = [var for var in required_env if not os.getenv(var)]
    
    if missing_env:
        print("❌ Missing required environment variables:")
        for var in missing_env:
            print(f"   - {var}")
        print("\nPlease configure your .env file and try again.")
        return False
    
    # Initialize system manager
    manager = RealWebExtractionSystem()
    manager.setup_signal_handlers()
    
    try:
        # Start all services
        if await manager.start_all_services():
            
            # Initialize web extraction agent
            await manager.init_web_agent()
            
            # Display system status
            manager.display_system_status()
            
            # Run initial extraction demo
            print("\n🚀 Running initial extraction demo...")
            await manager.run_real_extraction('hacker_news_top')
            
            # Start interactive menu
            await manager.interactive_menu()
            
        else:
            print("❌ Failed to start system")
            return False
            
    except KeyboardInterrupt:
        print("\n🛑 Received interrupt signal")
    except Exception as e:
        print(f"❌ System error: {e}")
    finally:
        await manager.shutdown_system()
    
    return True

if __name__ == "__main__":
    asyncio.run(main())
