#!/usr/bin/env python3
"""
Enhanced Startup with Real Browserbase Integration
================================================

This version integrates the working system with REAL Browserbase web extraction
instead of simulated data. Gives you the best of both worlds:
- Working email and database agents
- REAL web scraping with Browserbase headless browser
- Expandable to any website with JavaScript support

Run this to get REAL data extraction!
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
import requests

# Setup project paths
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

class EnhancedSystemManager:
    """Enhanced system manager with real Browserbase integration"""
    
    def __init__(self):
        self.processes = {}
        self.services_status = {}
        self.shutdown_flag = False
        
        # Check Browserbase configuration
        self.browserbase_available = bool(os.getenv("BROWSERBASE_API_KEY"))
        self.extraction_mode = "REAL BROWSERBASE" if self.browserbase_available else "SIMULATED"
        
        print(f"🌐 Enhanced Startup - {self.extraction_mode} Extraction Mode")
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
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            print(f"\n⚠️  Received signal {signum}. Initiating graceful shutdown...")
            self.shutdown_flag = True
            asyncio.create_task(self.shutdown_system())
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
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
            
            # Check if the service is responsive
            is_responsive = await self.check_service_health(config["port"])
            
            if is_responsive:
                print(f"✅ {config['name']} started successfully")
                self.services_status[service_id] = "running"
                return True
            else:
                print(f"⚠️  {config['name']} started but may not be fully ready")
                self.services_status[service_id] = "starting"
                return True
                
        except Exception as e:
            print(f"❌ Failed to start {config['name']}: {e}")
            self.services_status[service_id] = "failed"
            return False
    
    async def check_service_health(self, port: int) -> bool:
        """Check if service is responsive"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{port}/health",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    return response.status == 200
        except:
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
        
        if success_count == total_services:
            print("✅ All services started successfully!")
            return True
        elif success_count > 0:
            print("⚠️  Some services started - system partially operational")
            return True
        else:
            print("❌ No services started - system failed to start")
            return False
    
    def display_system_status(self):
        """Display current system status"""
        print("\n🎯 ENHANCED MCP MULTI-AGENT SYSTEM STATUS")
        print("=" * 60)
        print(f"Extraction Mode: {self.extraction_mode}")
        print(f"Browserbase API: {'✅ Configured' if self.browserbase_available else '❌ Not configured'}")
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
        
        print("\n🌐 REAL WEB EXTRACTION CAPABILITIES:")
        if self.browserbase_available:
            print("✅ Yahoo Finance - Semiconductor stocks")
            print("✅ CoinMarketCap - Cryptocurrency data") 
            print("✅ Hacker News - Tech news")
            print("✅ GitHub Trending - Popular repositories")
            print("✅ Any website with JavaScript support")
        else:
            print("⚠️  Configure BROWSERBASE_API_KEY for real extraction")
        
        print("\n📧 EMAIL NOTIFICATIONS:")
        email_configured = os.getenv("SMTP_SERVER") and os.getenv("SMTP_USERNAME")
        print(f"{'✅' if email_configured else '⚠️ '} SMTP Configuration: {'Ready' if email_configured else 'Configure for real emails'}")
        print(f"📧 Target Email: {os.getenv('TARGET_EMAIL', 'rajpraba_1986@yahoo.com.sg')}")
    
    async def run_sample_extraction(self):
        """Run a sample extraction workflow"""
        print("\n🚀 RUNNING SAMPLE EXTRACTION WORKFLOW")
        print("=" * 50)
        
        try:
            # Import and run the enhanced Browserbase agent
            from enhanced_browserbase_agent import EnhancedBrowserbaseAgent
            from langchain_anthropic import ChatAnthropic
            
            # Initialize Claude LLM
            llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                temperature=0.1,
                api_key=os.getenv("ANTHROPIC_API_KEY")
            )
            
            # Create the enhanced agent
            agent = EnhancedBrowserbaseAgent(llm)
            
            # Run extraction workflow
            if self.browserbase_available:
                print("🌐 Running REAL Browserbase extraction...")
                result = await agent.run_extraction_workflow("yahoo_finance_semiconductors")
            else:
                print("⚠️  Running simulated extraction (configure Browserbase for real data)...")
                result = await agent.run_extraction_workflow("yahoo_finance_semiconductors")
            
            # Display results
            print("\n🎯 EXTRACTION RESULTS:")
            print(f"Status: {result.get('workflow_status')}")
            print(f"Method: {result.get('extraction_method')}")
            print(f"Items: {result.get('extracted_items')}")
            
            # Display database result
            db_result = result.get('database_result', {})
            print(f"Database: {db_result.get('status', 'unknown')}")
            
            # Display email result  
            email_result = result.get('email_result', {})
            print(f"Email: {email_result.get('status', 'unknown')}")
            
            # Show sample data
            sample_data = result.get('sample_data', [])
            if sample_data:
                print(f"\n📊 Sample Data (first 3 items):")
                for i, item in enumerate(sample_data, 1):
                    print(f"  {i}. {json.dumps(item, indent=4)}")
            
            return result
            
        except Exception as e:
            print(f"❌ Extraction workflow failed: {e}")
            return {"workflow_status": "failed", "error": str(e)}
    
    async def interactive_menu(self):
        """Interactive menu for system operations"""
        while not self.shutdown_flag:
            print("\n🎮 INTERACTIVE MENU")
            print("=" * 30)
            print("1. 🌐 Run Real Web Extraction")
            print("2. 📊 View System Status") 
            print("3. 🔄 Restart Services")
            print("4. 📧 Test Email Notification")
            print("5. 🗃️  View Database Records")
            print("6. ⚙️  Configure Browserbase")
            print("7. 🛑 Shutdown System")
            
            try:
                choice = input("\nEnter choice (1-7): ").strip()
                
                if choice == "1":
                    await self.run_sample_extraction()
                elif choice == "2":
                    self.display_system_status()
                elif choice == "3":
                    await self.restart_services()
                elif choice == "4":
                    await self.test_email_notification()
                elif choice == "5":
                    await self.view_database_records()
                elif choice == "6":
                    await self.configure_browserbase()
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
        
        try:
            import aiohttp
            
            test_data = [{
                "symbol": "TEST",
                "price": "$100.00",
                "change": "+5.00%",
                "source": "test",
                "method": self.extraction_mode
            }]
            
            request_data = {
                "jsonrpc": "2.0",
                "id": "test_email",
                "method": "send_extraction_notification",
                "params": {
                    "extraction_source": "test_extraction",
                    "data_count": 1,
                    "extraction_data": test_data,
                    "extraction_method": self.extraction_mode.lower()
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8003/mcp/request",
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            print("✅ Email test successful!")
                        else:
                            print(f"⚠️  Email test returned: {result}")
                    else:
                        print(f"❌ Email test failed: HTTP {response.status}")
                        
        except Exception as e:
            print(f"❌ Email test error: {e}")
    
    async def view_database_records(self):
        """View recent database records"""
        print("🗃️  Fetching recent database records...")
        
        try:
            import aiohttp
            
            request_data = {
                "jsonrpc": "2.0",
                "id": "get_records",
                "method": "get_recent_extractions",
                "params": {"limit": 5}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:8002/mcp/request", 
                    json=request_data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            records = result["result"]["records"]
                            print(f"📊 Found {len(records)} recent records:")
                            for i, record in enumerate(records, 1):
                                print(f"  {i}. ID: {record.get('id')}")
                                print(f"     Source: {record.get('source')}")
                                print(f"     Time: {record.get('created_at')}")
                                print(f"     Items: {len(record.get('data', []))}")
                        else:
                            print(f"⚠️  Database query returned: {result}")
                    else:
                        print(f"❌ Database query failed: HTTP {response.status}")
                        
        except Exception as e:
            print(f"❌ Database query error: {e}")
    
    async def configure_browserbase(self):
        """Interactive Browserbase configuration"""
        print("⚙️  BROWSERBASE CONFIGURATION")
        print("=" * 40)
        
        current_key = os.getenv("BROWSERBASE_API_KEY")
        current_project = os.getenv("BROWSERBASE_PROJECT_ID")
        
        print(f"Current API Key: {'✅ Configured' if current_key else '❌ Not set'}")
        print(f"Current Project: {'✅ Configured' if current_project else '❌ Not set'}")
        
        if current_key:
            print("\n🌐 Browserbase is ready for REAL web extraction!")
            print("Available extraction targets:")
            print("• Yahoo Finance Semiconductors")
            print("• CoinMarketCap Crypto Data")
            print("• Hacker News Tech Stories")
            print("• GitHub Trending Repos")
        else:
            print("\n📝 To enable REAL web extraction:")
            print("1. Sign up at https://browserbase.com")
            print("2. Get your API key and Project ID")
            print("3. Add to your .env file:")
            print("   BROWSERBASE_API_KEY=your_api_key_here")
            print("   BROWSERBASE_PROJECT_ID=your_project_id_here")
    
    async def restart_services(self):
        """Restart all services"""
        print("🔄 Restarting services...")
        await self.shutdown_system()
        await asyncio.sleep(2)
        await self.start_all_services()
    
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
    print("🌟 ENHANCED MCP MULTI-AGENT SYSTEM")
    print("🌐 Real Web Extraction with Browserbase")
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
    manager = EnhancedSystemManager()
    manager.setup_signal_handlers()
    
    try:
        # Start all services
        if await manager.start_all_services():
            
            # Display system status
            manager.display_system_status()
            
            # Run initial extraction
            print("\n🚀 Running initial extraction workflow...")
            await manager.run_sample_extraction()
            
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
