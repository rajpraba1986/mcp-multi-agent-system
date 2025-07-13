#!/usr/bin/env python3
"""
Quick diagnostic script for MCP Multi-Agent System
Run this script to check overall system health

Usage:
    python diagnostic.py

This script performs comprehensive health checks for:
- System resources (CPU, memory)
- Required files and directories
- Environment variables
- Agent connectivity
- Database health
"""

import asyncio
import aiohttp
import sqlite3
import os
import time
from datetime import datetime

# Optional: Include psutil if available, fallback to basic checks
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("Note: psutil not available. Install with 'pip install psutil' for detailed system monitoring.")

class Colors:
    """Console color codes for better output formatting."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

def colored_print(text, color=Colors.END):
    """Print colored text."""
    print(f"{color}{text}{Colors.END}")

async def check_system_resources():
    """Check system resource usage."""
    colored_print("1️⃣ System Resources", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    
    if HAS_PSUTIL:
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            print(f"CPU Usage: {cpu_percent:.1f}%")
            
            if cpu_percent > 80:
                colored_print("⚠️  WARNING: High CPU usage", Colors.YELLOW)
                issues += 1
            
            # Memory usage
            memory = psutil.virtual_memory()
            print(f"Memory Usage: {memory.percent:.1f}% ({memory.used//(1024**3)}GB/{memory.total//(1024**3)}GB)")
            
            if memory.percent > 80:
                colored_print("⚠️  WARNING: High memory usage", Colors.YELLOW)
                issues += 1
            
            # Check Python processes
            python_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    if proc.info['name'] and 'python' in proc.info['name'].lower():
                        python_processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            print(f"Python processes: {len(python_processes)}")
            
            total_python_memory = sum(
                proc['memory_info'].rss if proc['memory_info'] else 0 
                for proc in python_processes
            )
            python_memory_mb = total_python_memory // (1024**2)
            
            if python_memory_mb > 1000:  # More than 1GB
                colored_print(f"⚠️  WARNING: High Python memory usage: {python_memory_mb}MB", Colors.YELLOW)
                issues += 1
            
        except Exception as e:
            colored_print(f"❌ Error checking system resources: {e}", Colors.RED)
            issues += 1
    else:
        colored_print("System resource checking requires psutil package", Colors.YELLOW)
    
    print()
    return issues

def check_required_files():
    """Check if all required files exist."""
    colored_print("2️⃣ Required Files", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    
    required_files = [
        "src/hub/mcp_hub.py",
        "src/agents/database_agent.py",
        "src/agents/browserbase_agent.py",
        "src/agents/email_agent.py"
    ]
    
    optional_files = [
        "data/demo.db",
        "requirements.txt",
        "README.md"
    ]
    
    # Check required files
    for file_path in required_files:
        if os.path.exists(file_path):
            colored_print(f"✅ {file_path}", Colors.GREEN)
        else:
            colored_print(f"❌ {file_path} - MISSING", Colors.RED)
            issues += 1
    
    # Check optional files
    for file_path in optional_files:
        if os.path.exists(file_path):
            colored_print(f"✅ {file_path} (optional)", Colors.GREEN)
        else:
            colored_print(f"⚠️  {file_path} - MISSING (optional)", Colors.YELLOW)
    
    # Check directory structure
    required_dirs = [
        "src",
        "src/hub",
        "src/agents",
        "src/client"
    ]
    
    for dir_path in required_dirs:
        if os.path.isdir(dir_path):
            colored_print(f"✅ Directory: {dir_path}", Colors.GREEN)
        else:
            colored_print(f"❌ Directory: {dir_path} - MISSING", Colors.RED)
            issues += 1
    
    print()
    return issues

def check_environment_variables():
    """Check required environment variables."""
    colored_print("3️⃣ Environment Variables", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    
    required_vars = ["ANTHROPIC_API_KEY"]
    optional_vars = ["BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID", "OPENAI_API_KEY"]
    
    # Check required variables
    for var in required_vars:
        value = os.getenv(var)
        if value:
            masked_value = '*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)
            colored_print(f"✅ {var}: {masked_value}", Colors.GREEN)
        else:
            colored_print(f"❌ {var}: NOT SET", Colors.RED)
            issues += 1
    
    # Check optional variables
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            masked_value = '*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)
            colored_print(f"✅ {var}: {masked_value} (optional)", Colors.GREEN)
        else:
            colored_print(f"⚠️  {var}: NOT SET (optional)", Colors.YELLOW)
    
    print()
    return issues

async def check_agent_connectivity():
    """Check connectivity to all agents."""
    colored_print("4️⃣ Agent Connectivity", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    
    agents_to_check = [
        ("Hub", "http://localhost:5000/health"),
        ("BrowserbaseAgent", "http://localhost:8001/health"),
        ("DatabaseAgent", "http://localhost:8002/health"),
        ("EmailAgent", "http://localhost:8003/health")
    ]
    
    for name, url in agents_to_check:
        try:
            start_time = time.time()
            timeout = aiohttp.ClientTimeout(total=5)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    
                    if response.status == 200:
                        colored_print(f"✅ {name}: {response_time:.3f}s", Colors.GREEN)
                    else:
                        colored_print(f"❌ {name}: HTTP {response.status} ({response_time:.3f}s)", Colors.RED)
                        issues += 1
                        
        except asyncio.TimeoutError:
            colored_print(f"❌ {name}: Timeout (>5s)", Colors.RED)
            issues += 1
        except Exception as e:
            error_msg = str(e)[:50] + "..." if len(str(e)) > 50 else str(e)
            colored_print(f"❌ {name}: {error_msg}", Colors.RED)
            issues += 1
    
    print()
    return issues

def check_database_health():
    """Check database connectivity and basic operations."""
    colored_print("5️⃣ Database Health", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    db_path = "data/demo.db"
    
    try:
        # Check if database file exists
        if not os.path.exists(db_path):
            colored_print(f"⚠️  Database file doesn't exist: {db_path}", Colors.YELLOW)
            colored_print("This is normal if no data has been stored yet.", Colors.YELLOW)
            print()
            return 0
        
        # Check file permissions
        if not os.access(db_path, os.R_OK):
            colored_print(f"❌ Database file not readable: {db_path}", Colors.RED)
            issues += 1
            
        if not os.access(db_path, os.W_OK):
            colored_print(f"❌ Database file not writable: {db_path}", Colors.RED)
            issues += 1
        
        # Test database connection
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        table_names = [table[0] for table in tables]
        
        if 'extractions' in table_names:
            cursor.execute("SELECT COUNT(*) FROM extractions")
            count = cursor.fetchone()[0]
            colored_print(f"✅ Database accessible: {count} records in extractions table", Colors.GREEN)
        else:
            colored_print("⚠️  Extractions table not found (will be created when needed)", Colors.YELLOW)
        
        colored_print(f"✅ Database tables: {', '.join(table_names) if table_names else 'None'}", Colors.GREEN)
        
        # Test basic write operation
        try:
            cursor.execute("CREATE TEMPORARY TABLE test_table (id INTEGER)")
            cursor.execute("DROP TABLE test_table")
            colored_print("✅ Database write operations working", Colors.GREEN)
        except Exception as e:
            colored_print(f"❌ Database write test failed: {e}", Colors.RED)
            issues += 1
        
        conn.close()
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            colored_print(f"❌ Database is locked (another process may be using it)", Colors.RED)
        else:
            colored_print(f"❌ Database operational error: {e}", Colors.RED)
        issues += 1
    except Exception as e:
        colored_print(f"❌ Database error: {e}", Colors.RED)
        issues += 1
    
    print()
    return issues

async def check_network_ports():
    """Check if required network ports are available."""
    colored_print("6️⃣ Network Ports", Colors.BLUE)
    colored_print("-" * 20)
    
    issues = 0
    ports_to_check = [5000, 8001, 8002, 8003]
    
    for port in ports_to_check:
        try:
            # Try to connect to the port
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection('localhost', port),
                timeout=2.0
            )
            writer.close()
            await writer.wait_closed()
            colored_print(f"✅ Port {port}: Service responding", Colors.GREEN)
            
        except asyncio.TimeoutError:
            colored_print(f"❌ Port {port}: Timeout (service may be down)", Colors.RED)
            issues += 1
        except ConnectionRefusedError:
            colored_print(f"❌ Port {port}: Connection refused (service not running)", Colors.RED)
            issues += 1
        except Exception as e:
            colored_print(f"❌ Port {port}: {str(e)[:40]}...", Colors.RED)
            issues += 1
    
    print()
    return issues

def suggest_fixes(total_issues):
    """Provide suggestions based on issues found."""
    if total_issues == 0:
        return
    
    colored_print("🔧 Suggested Fixes", Colors.YELLOW)
    colored_print("-" * 20)
    
    print("Common solutions:")
    print("1. Start the hub: python src/hub/mcp_hub.py")
    print("2. Start agents individually:")
    print("   - python src/agents/database_agent.py")
    print("   - python src/agents/browserbase_agent.py")
    print("   - python src/agents/email_agent.py")
    print("3. Set environment variables:")
    print("   - $env:ANTHROPIC_API_KEY = 'your-api-key'")
    print("   - $env:BROWSERBASE_API_KEY = 'your-browserbase-key'")
    print("4. Check Windows firewall settings")
    print("5. Restart any hung Python processes")
    print()

async def run_full_diagnostic():
    """Run comprehensive system diagnostic."""
    
    colored_print("🏥 MCP Multi-Agent System Health Check", Colors.BOLD)
    colored_print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Working Directory: {os.getcwd()}")
    print()
    
    total_issues = 0
    
    # Run all diagnostic checks
    total_issues += await check_system_resources()
    total_issues += check_required_files()
    total_issues += check_environment_variables()
    total_issues += await check_agent_connectivity()
    total_issues += check_database_health()
    total_issues += await check_network_ports()
    
    # Summary
    colored_print("📋 Diagnostic Summary", Colors.BOLD)
    colored_print("-" * 20)
    
    if total_issues == 0:
        colored_print("🎉 All checks passed! System is healthy.", Colors.GREEN)
        print("\nThe MCP Multi-Agent System appears to be running correctly.")
        print("You can now use the agents for data extraction, storage, and automation tasks.")
    else:
        colored_print(f"⚠️  Found {total_issues} issue(s) that need attention.", Colors.YELLOW)
        suggest_fixes(total_issues)
    
    return total_issues == 0

def main():
    """Main entry point."""
    try:
        success = asyncio.run(run_full_diagnostic())
        return 0 if success else 1
    except KeyboardInterrupt:
        colored_print("\n\n❌ Diagnostic interrupted by user", Colors.RED)
        return 1
    except Exception as e:
        colored_print(f"\n\n❌ Diagnostic failed with error: {e}", Colors.RED)
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
