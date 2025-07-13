# Troubleshooting Guide for MCP Multi-Agent System

## 🔧 Common Issues and Solutions

### 1. Agent Discovery Issues

#### Problem: "Agent not found" or "No agents discovered"

**Symptoms:**
- Agents don't appear in discovery calls
- Hub returns empty agent list
- Connection timeouts during discovery

**Diagnosis Steps:**
```python
# Check hub connectivity
async def diagnose_hub_connection():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:5000/health") as response:
                if response.status == 200:
                    print("✅ Hub is running and accessible")
                    return True
                else:
                    print(f"❌ Hub responded with status: {response.status}")
                    return False
    except Exception as e:
        print(f"❌ Hub connection failed: {e}")
        return False

# Check agent registration
async def diagnose_agent_registration():
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:5000/agents") as response:
                agents = await response.json()
                print(f"Registered agents: {len(agents)}")
                for agent in agents:
                    print(f"  - {agent.get('agent_type', 'unknown')} at {agent.get('endpoint_url', 'unknown')}")
                return agents
    except Exception as e:
        print(f"❌ Failed to get agent list: {e}")
        return []
```

**Solutions:**

1. **Check Hub Status:**
   ```powershell
   # Check if hub is running
   Get-Process -Name python | Where-Object {$_.CommandLine -like "*hub.py*"}
   
   # Check port availability
   netstat -an | findstr :5000
   ```

2. **Restart Hub Service:**
   ```powershell
   # Navigate to project directory
   cd c:\Users\prajen1\AgenticAIWorkspace\MCPToolCalling
   
   # Stop any existing hub processes
   Get-Process python | Where-Object {$_.CommandLine -like "*hub.py*"} | Stop-Process
   
   # Start hub
   python agents/hub/hub.py
   ```

3. **Check Agent Registration:**
   ```python
   # Manual agent registration
   import asyncio
   import aiohttp
   
   async def register_agent():
       agent_info = {
           "agent_type": "data_storage",
           "endpoint_url": "http://localhost:8002/mcp",
           "capabilities": ["store_data", "query_data"],
           "status": "active"
       }
       
       async with aiohttp.ClientSession() as session:
           async with session.post(
               "http://localhost:5000/register",
               json=agent_info
           ) as response:
               result = await response.text()
               print(f"Registration result: {result}")
   
   asyncio.run(register_agent())
   ```

4. **Network Connectivity Issues:**
   ```powershell
   # Test local connectivity
   curl http://localhost:5000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   
   # Check firewall settings
   Get-NetFirewallRule | Where-Object {$_.DisplayName -like "*Python*"}
   ```

### 2. Agent Communication Failures

#### Problem: "Connection refused" or timeout errors

**Symptoms:**
- Agents discovered but calls fail
- Intermittent connection errors
- Slow response times

**Diagnosis:**
```python
async def diagnose_agent_health():
    """Check health of all discovered agents."""
    
    # Discover agents
    async with aiohttp.ClientSession() as session:
        async with session.get("http://localhost:5000/agents") as response:
            agents = await response.json()
    
    # Test each agent
    for agent in agents:
        endpoint = agent.get("endpoint_url", "")
        agent_type = agent.get("agent_type", "unknown")
        
        try:
            # Test basic connectivity
            health_url = endpoint.replace("/mcp", "/health")
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(health_url) as response:
                    if response.status == 200:
                        print(f"✅ {agent_type} - Health check passed")
                        
                        # Test MCP endpoint
                        test_request = {
                            "jsonrpc": "2.0",
                            "id": "test",
                            "method": "tools/list",
                            "params": {}
                        }
                        
                        async with session.post(endpoint, json=test_request) as mcp_response:
                            if mcp_response.status == 200:
                                print(f"✅ {agent_type} - MCP endpoint working")
                            else:
                                print(f"❌ {agent_type} - MCP endpoint failed: {mcp_response.status}")
                    else:
                        print(f"❌ {agent_type} - Health check failed: {response.status}")
        
        except asyncio.TimeoutError:
            print(f"❌ {agent_type} - Timeout (agent may be overloaded)")
        except Exception as e:
            print(f"❌ {agent_type} - Connection failed: {e}")

# Run diagnosis
asyncio.run(diagnose_agent_health())
```

**Solutions:**

1. **Check Agent Processes:**
   ```powershell
   # List all Python processes
   Get-Process python | Format-Table Id, ProcessName, @{Name="CommandLine";Expression={$_.CommandLine}}
   
   # Check specific agent ports
   netstat -an | findstr "8001 8002 8003 5000"
   ```

2. **Restart Individual Agents:**
   ```powershell
   # Stop specific agent
   Get-Process python | Where-Object {$_.CommandLine -like "*database_agent.py*"} | Stop-Process
   
   # Start agent
   python agents/database_agent/database_agent.py
   ```

3. **Check Agent Logs:**
   ```python
   # Enable detailed logging
   import logging
   logging.basicConfig(level=logging.DEBUG)
   
   # Check agent-specific logs
   # Most agents log to console and files in logs/ directory
   ```

4. **Resource Issues:**
   ```powershell
   # Check system resources
   Get-Counter "\Processor(_Total)\% Processor Time"
   Get-Counter "\Memory\Available MBytes"
   
   # Check Python memory usage
   Get-Process python | Measure-Object WorkingSet -Sum
   ```

### 3. Authentication and Authorization Issues

#### Problem: "Unauthorized" or permission denied errors

**Symptoms:**
- 401/403 HTTP status codes
- "Access denied" messages
- LLM API key errors

**Solutions:**

1. **Check API Keys:**
   ```python
   import os
   
   # Verify environment variables
   required_keys = ["ANTHROPIC_API_KEY", "BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID"]
   
   for key in required_keys:
       value = os.getenv(key)
       if value:
           print(f"✅ {key}: {'*' * (len(value) - 8) + value[-8:]}")
       else:
           print(f"❌ {key}: Not set")
   ```

2. **Update Environment Variables:**
   ```powershell
   # Set in current session
   $env:ANTHROPIC_API_KEY = "your-key-here"
   $env:BROWSERBASE_API_KEY = "your-browserbase-key"
   $env:BROWSERBASE_PROJECT_ID = "your-project-id"
   
   # Set permanently
   [Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "your-key-here", "User")
   ```

3. **Test API Connectivity:**
   ```python
   import anthropic
   import os
   
   async def test_anthropic_api():
       try:
           client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
           
           response = client.messages.create(
               model="claude-3-haiku-20240307",
               max_tokens=10,
               messages=[{"role": "user", "content": "Hello"}]
           )
           
           print("✅ Anthropic API working")
           return True
       except Exception as e:
           print(f"❌ Anthropic API failed: {e}")
           return False
   
   asyncio.run(test_anthropic_api())
   ```

### 4. Database Connection Issues

#### Problem: Database operations fail

**Symptoms:**
- SQLite file access errors
- Database locked errors
- Data not persisting

**Diagnosis:**
```python
import sqlite3
import os

def diagnose_database():
    db_path = "agents/database_agent/extractions.db"
    
    # Check file existence and permissions
    if os.path.exists(db_path):
        print(f"✅ Database file exists: {db_path}")
        
        # Check file size
        size = os.path.getsize(db_path)
        print(f"📊 Database size: {size} bytes")
        
        # Check permissions
        print(f"📋 Readable: {os.access(db_path, os.R_OK)}")
        print(f"📋 Writable: {os.access(db_path, os.W_OK)}")
        
    else:
        print(f"❌ Database file not found: {db_path}")
        return False
    
    # Test connection
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f"✅ Database connection successful")
        print(f"📊 Tables found: {[table[0] for table in tables]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

# Run diagnosis
diagnose_database()
```

**Solutions:**

1. **Fix Database Permissions:**
   ```powershell
   # Check file permissions
   Get-Acl "agents\database_agent\extractions.db"
   
   # Fix permissions if needed
   icacls "agents\database_agent\extractions.db" /grant Everyone:F
   ```

2. **Recreate Database:**
   ```python
   import sqlite3
   import os
   
   def recreate_database():
       db_path = "agents/database_agent/extractions.db"
       
       # Backup existing database
       if os.path.exists(db_path):
           backup_path = f"{db_path}.backup"
           os.rename(db_path, backup_path)
           print(f"Database backed up to: {backup_path}")
       
       # Create new database
       conn = sqlite3.connect(db_path)
       cursor = conn.cursor()
       
       # Create tables
       cursor.execute('''
           CREATE TABLE IF NOT EXISTS extractions (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               url TEXT NOT NULL,
               title TEXT,
               content TEXT,
               extracted_data TEXT,
               extraction_type TEXT DEFAULT 'general',
               metadata TEXT,
               created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
           )
       ''')
       
       conn.commit()
       conn.close()
       print(f"✅ Database recreated: {db_path}")
   
   recreate_database()
   ```

3. **Handle Database Locks:**
   ```python
   import sqlite3
   import time
   
   def robust_database_operation(query, params=None, retries=3):
       """Execute database operation with retry logic."""
       
       for attempt in range(retries):
           try:
               conn = sqlite3.connect("agents/database_agent/extractions.db", timeout=10.0)
               cursor = conn.cursor()
               
               if params:
                   cursor.execute(query, params)
               else:
                   cursor.execute(query)
               
               conn.commit()
               result = cursor.fetchall()
               conn.close()
               
               return result
               
           except sqlite3.OperationalError as e:
               if "database is locked" in str(e) and attempt < retries - 1:
                   print(f"Database locked, retrying in {2 ** attempt} seconds...")
                   time.sleep(2 ** attempt)
                   continue
               else:
                   raise e
   ```

### 5. Performance Issues

#### Problem: Slow response times or timeouts

**Symptoms:**
- Operations taking longer than expected
- Timeout errors
- High CPU/memory usage

**Diagnosis:**
```python
import time
import psutil
import asyncio

async def performance_diagnostic():
    """Comprehensive performance analysis."""
    
    print("🔍 System Performance Analysis")
    print("=" * 50)
    
    # System resources
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    print(f"💻 CPU Usage: {cpu_percent}%")
    print(f"🧠 Memory Usage: {memory.percent}% ({memory.used // (1024**3)}GB / {memory.total // (1024**3)}GB)")
    print(f"💾 Disk Usage: {disk.percent}% ({disk.used // (1024**3)}GB / {disk.total // (1024**3)}GB)")
    
    # Python processes
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'cpu_percent', 'memory_info']):
        if proc.info['name'] == 'python.exe':
            python_processes.append(proc.info)
    
    print(f"\n🐍 Python Processes: {len(python_processes)}")
    for proc in python_processes:
        cmdline = ' '.join(proc['cmdline']) if proc['cmdline'] else 'N/A'
        memory_mb = proc['memory_info'].rss // (1024**2) if proc['memory_info'] else 0
        print(f"  PID {proc['pid']}: {memory_mb}MB - {cmdline[:80]}...")
    
    # Test agent response times
    print(f"\n⏱️ Agent Response Times:")
    agents = [
        ("Hub", "http://localhost:5000/health"),
        ("BrowserbaseAgent", "http://localhost:8001/health"),
        ("DatabaseAgent", "http://localhost:8002/health"),
        ("EmailAgent", "http://localhost:8003/health")
    ]
    
    for name, url in agents:
        start_time = time.time()
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    if response.status == 200:
                        print(f"  ✅ {name}: {response_time:.3f}s")
                    else:
                        print(f"  ❌ {name}: {response_time:.3f}s (Status: {response.status})")
        except Exception as e:
            response_time = time.time() - start_time
            print(f"  ❌ {name}: {response_time:.3f}s (Error: {str(e)[:30]}...)")

# Run diagnostic
asyncio.run(performance_diagnostic())
```

**Solutions:**

1. **Optimize Agent Configuration:**
   ```python
   # In agent configurations, adjust these settings:
   
   # Increase timeout values
   AGENT_TIMEOUT = 60  # seconds
   HTTP_TIMEOUT = 30   # seconds
   
   # Limit concurrent operations
   MAX_CONCURRENT_REQUESTS = 5
   
   # Configure connection pooling
   import aiohttp
   
   connector = aiohttp.TCPConnector(
       limit=100,           # Total connection pool size
       limit_per_host=30,   # Per-host connection limit
       ttl_dns_cache=300,   # DNS cache TTL
       use_dns_cache=True,
   )
   ```

2. **Implement Caching:**
   ```python
   import asyncio
   from functools import wraps
   
   # Simple in-memory cache
   _cache = {}
   
   def cache_result(ttl_seconds=300):
       def decorator(func):
           @wraps(func)
           async def wrapper(*args, **kwargs):
               # Create cache key
               cache_key = f"{func.__name__}:{hash(str(args) + str(kwargs))}"
               
               # Check cache
               if cache_key in _cache:
                   result, timestamp = _cache[cache_key]
                   if time.time() - timestamp < ttl_seconds:
                       return result
               
               # Execute function and cache result
               result = await func(*args, **kwargs)
               _cache[cache_key] = (result, time.time())
               
               return result
           return wrapper
       return decorator
   
   # Usage
   @cache_result(ttl_seconds=600)  # Cache for 10 minutes
   async def expensive_operation(data):
       # Your expensive operation here
       pass
   ```

3. **Monitor Resource Usage:**
   ```python
   import asyncio
   import logging
   import psutil
   
   class ResourceMonitor:
       def __init__(self, check_interval=30):
           self.check_interval = check_interval
           self.monitoring = False
       
       async def start_monitoring(self):
           self.monitoring = True
           while self.monitoring:
               try:
                   # Check system resources
                   cpu_percent = psutil.cpu_percent()
                   memory_percent = psutil.virtual_memory().percent
                   
                   if cpu_percent > 80:
                       logging.warning(f"High CPU usage: {cpu_percent}%")
                   
                   if memory_percent > 80:
                       logging.warning(f"High memory usage: {memory_percent}%")
                   
                   # Check Python processes
                   python_memory = 0
                   for proc in psutil.process_iter(['name', 'memory_info']):
                       if proc.info['name'] == 'python.exe':
                           python_memory += proc.info['memory_info'].rss
                   
                   python_memory_mb = python_memory // (1024**2)
                   if python_memory_mb > 1000:  # More than 1GB
                       logging.warning(f"High Python memory usage: {python_memory_mb}MB")
                   
               except Exception as e:
                   logging.error(f"Resource monitoring error: {e}")
               
               await asyncio.sleep(self.check_interval)
       
       def stop_monitoring(self):
           self.monitoring = False
   
   # Start monitoring
   monitor = ResourceMonitor()
   asyncio.create_task(monitor.start_monitoring())
   ```

### 6. Environment-Specific Issues

#### Problem: Issues specific to Windows environment

**Common Windows Issues:**

1. **PowerShell Execution Policy:**
   ```powershell
   # Check current policy
   Get-ExecutionPolicy
   
   # Set policy to allow script execution
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

2. **Path Issues:**
   ```powershell
   # Use forward slashes or escape backslashes in Python
   # Correct:
   db_path = "agents/database_agent/extractions.db"
   # or
   db_path = "agents\\database_agent\\extractions.db"
   
   # Check Python path
   python -c "import sys; print('\n'.join(sys.path))"
   ```

3. **Port Conflicts:**
   ```powershell
   # Check what's using specific ports
   netstat -ano | findstr :5000
   netstat -ano | findstr :8001
   
   # Kill process using port (replace PID)
   taskkill /PID 1234 /F
   ```

4. **Python Virtual Environment:**
   ```powershell
   # Create virtual environment
   python -m venv mcp_env
   
   # Activate virtual environment
   .\mcp_env\Scripts\Activate.ps1
   
   # Install requirements
   pip install -r requirements.txt
   ```

### 7. Quick Diagnostic Script

```python
#!/usr/bin/env python3
"""
Quick diagnostic script for MCP Multi-Agent System
Run this script to check overall system health
"""

import asyncio
import aiohttp
import sqlite3
import os
import psutil
import time
from datetime import datetime

async def run_full_diagnostic():
    """Run comprehensive system diagnostic."""
    
    print("🏥 MCP Multi-Agent System Health Check")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    issues_found = 0
    
    # 1. Check system resources
    print("1️⃣ System Resources")
    print("-" * 20)
    
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    print(f"CPU Usage: {cpu_percent:.1f}%")
    print(f"Memory Usage: {memory.percent:.1f}% ({memory.used//(1024**3)}GB/{memory.total//(1024**3)}GB)")
    
    if cpu_percent > 80:
        print("⚠️  WARNING: High CPU usage")
        issues_found += 1
    if memory.percent > 80:
        print("⚠️  WARNING: High memory usage")
        issues_found += 1
    
    print()
    
    # 2. Check required files
    print("2️⃣ Required Files")
    print("-" * 20)
    
    required_files = [
        "agents/hub/hub.py",
        "agents/database_agent/database_agent.py",
        "agents/browserbase_agent/browserbase_agent.py",
        "agents/email_agent/email_agent.py",
        "agents/database_agent/extractions.db"
    ]
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path} - MISSING")
            issues_found += 1
    
    print()
    
    # 3. Check environment variables
    print("3️⃣ Environment Variables")
    print("-" * 20)
    
    env_vars = ["ANTHROPIC_API_KEY", "BROWSERBASE_API_KEY", "BROWSERBASE_PROJECT_ID"]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * (len(value) - 8) + value[-8:] if len(value) > 8 else '*' * len(value)}")
        else:
            print(f"❌ {var}: NOT SET")
            issues_found += 1
    
    print()
    
    # 4. Check agent connectivity
    print("4️⃣ Agent Connectivity")
    print("-" * 20)
    
    agents_to_check = [
        ("Hub", "http://localhost:5000/health"),
        ("BrowserbaseAgent", "http://localhost:8001/health"),
        ("DatabaseAgent", "http://localhost:8002/health"),
        ("EmailAgent", "http://localhost:8003/health")
    ]
    
    for name, url in agents_to_check:
        try:
            start_time = time.time()
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(url) as response:
                    response_time = time.time() - start_time
                    if response.status == 200:
                        print(f"✅ {name}: {response_time:.3f}s")
                    else:
                        print(f"❌ {name}: HTTP {response.status}")
                        issues_found += 1
        except Exception as e:
            print(f"❌ {name}: {str(e)[:50]}...")
            issues_found += 1
    
    print()
    
    # 5. Check database
    print("5️⃣ Database Health")
    print("-" * 20)
    
    try:
        conn = sqlite3.connect("agents/database_agent/extractions.db", timeout=5.0)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM extractions")
        count = cursor.fetchone()[0]
        print(f"✅ Database accessible: {count} records")
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")
        issues_found += 1
    
    print()
    
    # Summary
    print("📋 Diagnostic Summary")
    print("-" * 20)
    
    if issues_found == 0:
        print("🎉 All checks passed! System is healthy.")
    else:
        print(f"⚠️  Found {issues_found} issue(s) that need attention.")
        print("\nRecommended actions:")
        print("1. Check the specific errors above")
        print("2. Restart any failed agents")
        print("3. Verify environment variables are set")
        print("4. Check network connectivity")
        print("5. Review system resources")
    
    return issues_found == 0

if __name__ == "__main__":
    success = asyncio.run(run_full_diagnostic())
    exit(0 if success else 1)
```

**Save this script as `diagnostic.py` and run it whenever you encounter issues:**

```powershell
python diagnostic.py
```

This diagnostic script will quickly identify common issues and provide guidance on resolution steps.

---

**This troubleshooting guide covers the most common issues encountered in the MCP Multi-Agent System. For persistent issues, check the individual agent logs and consider restarting the entire system.**
