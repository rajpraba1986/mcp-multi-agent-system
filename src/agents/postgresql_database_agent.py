#!/usr/bin/env python3
"""
PostgreSQL Database Agent
========================

A real database agent that stores extraction data in PostgreSQL.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime

# Setup path
project_root = Path(__file__).parent
sys.path.append(str(project_root))
sys.path.append(str(project_root / "src"))

# Load environment
from dotenv import load_dotenv
load_dotenv()

# Core imports
from langchain_anthropic import ChatAnthropic
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import uvicorn
import aiohttp
import asyncpg

class PostgreSQLDatabaseAgent:
    """A real database agent using PostgreSQL for storage"""
    
    def __init__(self, llm, hub_url: str, agent_port: int):
        self.llm = llm
        self.hub_url = hub_url
        self.agent_port = agent_port
        self.app = FastAPI()
        self.agent_id = f"postgresql_database_agent_{agent_port}"
        self.db_pool = None
        self.setup_routes()
    
    async def init_database(self):
        """Initialize PostgreSQL connection and tables"""
        try:
            # Database connection parameters from .env
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'toolbox_demo'),
                'user': os.getenv('POSTGRES_USER', 'demo_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'demo_password')
            }
            
            print(f"🔗 Connecting to PostgreSQL: {db_config['host']}:{db_config['port']}/{db_config['database']}")
            
            # Create connection pool
            self.db_pool = await asyncpg.create_pool(
                host=db_config['host'],
                port=db_config['port'],
                database=db_config['database'],
                user=db_config['user'],
                password=db_config['password'],
                min_size=2,
                max_size=10
            )
            
            # Create tables for extracted data
            await self.create_extraction_tables()
            
            print("✅ PostgreSQL database initialized")
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            print("   CRITICAL: PostgreSQL is required for production")
            raise Exception(f"PostgreSQL connection failed: {e}. Please ensure PostgreSQL is running and configured correctly.")
    
    async def init_sqlite_fallback(self):
        """Initialize SQLite as fallback"""
        try:
            import aiosqlite
            
            self.db_path = project_root / "data" / "extraction_data.db"
            self.db_path.parent.mkdir(exist_ok=True)
            
            # Create tables
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                CREATE TABLE IF NOT EXISTS extraction_data (
                    id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    extraction_timestamp DATETIME NOT NULL,
                    data_type TEXT,
                    raw_data TEXT NOT NULL,
                    processed_data TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                await db.execute("""
                CREATE TABLE IF NOT EXISTS stock_data (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    company TEXT,
                    price REAL,
                    change_value TEXT,
                    volume TEXT,
                    extraction_id TEXT,
                    extracted_at DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (extraction_id) REFERENCES extraction_data (id)
                )
                """)
                
                await db.commit()
            
            print("✅ SQLite database initialized as fallback")
            return True
            
        except Exception as e:
            print(f"❌ SQLite fallback failed: {e}")
            return False
    
    async def create_extraction_tables(self):
        """Create tables for storing extraction data"""
        async with self.db_pool.acquire() as conn:
            # Main extraction data table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS extraction_data (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                source TEXT NOT NULL,
                extraction_timestamp TIMESTAMP NOT NULL,
                data_type TEXT,
                raw_data JSONB NOT NULL,
                processed_data JSONB,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
            
            # Specific table for stock data
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                symbol TEXT NOT NULL,
                company TEXT,
                price DECIMAL(10, 2),
                change_value TEXT,
                volume TEXT,
                extraction_id UUID,
                extracted_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (extraction_id) REFERENCES extraction_data (id)
            )
            """)
            
            # Index for better performance
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_extraction_source ON extraction_data (source)")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_stock_symbol ON stock_data (symbol)")
            
            print("✅ Database tables created/verified")
    
    def setup_routes(self):
        """Setup FastAPI routes for MCP protocol"""
        
        @self.app.post("/mcp/request")
        async def handle_mcp_request(request: Request):
            """Handle MCP requests"""
            try:
                data = await request.json()
                return await self.process_mcp_request(data)
            except Exception as e:
                return {"jsonrpc": "2.0", "error": {"code": -1, "message": str(e)}}
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "agent_id": self.agent_id, "database": "postgresql"}
        
        @self.app.get("/data")
        async def get_all_data():
            """Get all stored extraction data"""
            try:
                data = await self.get_all_extraction_data()
                return {"data": data, "count": len(data)}
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.get("/data/{extraction_id}")
        async def get_data_by_id(extraction_id: str):
            """Get specific extraction data by ID"""
            try:
                data = await self.get_extraction_by_id(extraction_id)
                return {"data": data}
            except Exception as e:
                return {"error": str(e)}
        
        @self.app.get("/stocks")
        async def get_stock_data():
            """Get all stored stock data"""
            try:
                data = await self.get_all_stock_data()
                return {"stocks": data, "count": len(data)}
            except Exception as e:
                return {"error": str(e)}
    
    async def process_mcp_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process MCP requests"""
        try:
            method = request_data.get("method")
            params = request_data.get("params", {})
            request_id = request_data.get("id")
            
            if method == "store_extraction_data":
                result = await self.store_extraction_data(params)
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result
                }
            elif method == "query_database":
                result = await self.query_database(params)
                return {
                    "jsonrpc": "2.0", 
                    "id": request_id,
                    "result": result
                }
            elif method == "get_extraction_data":
                result = await self.get_all_extraction_data()
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"data": result, "count": len(result)}
                }
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32601, "message": f"Method not found: {method}"}
                }
                
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_data.get("id"),
                "error": {"code": -1, "message": str(e)}
            }
    
    async def store_extraction_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Store extracted data in PostgreSQL database"""
        try:
            data = params.get("data", {})
            source = params.get("source", "unknown")
            timestamp = params.get("timestamp", str(datetime.now().timestamp()))
            metadata = params.get("metadata", {})
            
            # Generate extraction ID
            extraction_id = str(uuid.uuid4())
            extraction_timestamp = datetime.fromtimestamp(float(timestamp))
            
            print(f"💾 Storing extraction data...")
            print(f"   Source: {source}")
            print(f"   Data items: {len(data) if isinstance(data, list) else 1}")
            
            if self.db_pool:
                # Use PostgreSQL - Store in main extraction_data table only
                async with self.db_pool.acquire() as conn:
                    # Store main extraction record
                    await conn.execute("""
                    INSERT INTO extraction_data (id, source, extraction_timestamp, data_type, raw_data, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                    """, extraction_id, source, extraction_timestamp, "web_data", json.dumps(data), json.dumps(metadata))
                    
                    print(f"✅ Stored extraction data in PostgreSQL")
                    
                    return {
                        "status": "success",
                        "extraction_id": extraction_id,
                        "records_stored": 1,
                        "data_type": "web_data"
                    }
            else:
                # Fallback to SQLite
                import aiosqlite
                async with aiosqlite.connect(self.db_path) as db:
                    await db.execute("""
                    INSERT INTO extraction_data (id, source, extraction_timestamp, data_type, raw_data, metadata)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """, (extraction_id, source, extraction_timestamp.isoformat(), "web_data", json.dumps(data), json.dumps(metadata)))
                    
                    await db.commit()
                
                print(f"✅ Stored extraction data in SQLite (fallback)")
                
                return {
                    "status": "success", 
                    "extraction_id": extraction_id,
                    "records_stored": 1,
                    "summary": f"Stored extraction data from {source}",
                    "database_type": "sqlite_fallback"
                }
                
        except Exception as e:
            print(f"❌ Database storage failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_all_extraction_data(self) -> List[Dict[str, Any]]:
        """Get all extraction data from database"""
        try:
            if self.db_pool:
                async with self.db_pool.acquire() as conn:
                    rows = await conn.fetch("SELECT * FROM extraction_data ORDER BY created_at DESC")
                    return [dict(row) for row in rows]
            else:
                import aiosqlite
                async with aiosqlite.connect(self.db_path) as db:
                    async with db.execute("SELECT * FROM extraction_data ORDER BY created_at DESC") as cursor:
                        rows = await cursor.fetchall()
                        columns = [desc[0] for desc in cursor.description]
                        return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"❌ Failed to fetch extraction data: {e}")
            return []
    
    async def query_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query database for information"""
        query = params.get("query", "")
        
        # Use Claude to understand the query and generate appropriate response
        prompt = f"""
        You are a database agent. Process this query against stored extraction data:
        Query: {query}
        
        Available tables:
        - extraction_data: stores raw extraction records
        - stock_data: stores individual stock information
        
        Based on the query, suggest what data would be retrieved and how.
        """
        
        response = await self.llm.ainvoke(prompt)
        
        return {
            "query": query,
            "response": response.content,
            "status": "processed",
            "available_endpoints": {
                "all_extractions": "GET /data",
                "all_stocks": "GET /stocks",
                "specific_extraction": "GET /data/{id}"
            }
        }
    
    async def register_with_hub(self):
        """Register this agent with the MCP hub"""
        try:
            registration_request = {
                "jsonrpc": "2.0",
                "id": f"registration-{self.agent_id}",
                "method": "agents/register",
                "params": {
                    "agent_id": self.agent_id,
                    "agent_name": "PostgreSQL Database Agent",
                    "agent_type": "database",
                    "host": "localhost",
                    "port": self.agent_port,
                    "endpoint_url": f"http://localhost:{self.agent_port}/mcp/request",
                    "capabilities": [
                        {
                            "name": "store_extraction_data",
                            "description": "Store extracted data in PostgreSQL database",
                            "parameters": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "object", "description": "Data to store"},
                                    "source": {"type": "string", "description": "Data source"},
                                    "timestamp": {"type": "string", "description": "Extraction timestamp"}
                                },
                                "required": ["data", "source"]
                            }
                        },
                        {
                            "name": "get_extraction_data",
                            "description": "Retrieve stored extraction data",
                            "parameters": {"type": "object", "properties": {}}
                        }
                    ],
                    "status": "active"
                }
            }
            
            async with aiohttp.ClientSession() as session:
                hub_mcp_url = "http://localhost:5000/mcp"
                async with session.post(hub_mcp_url, json=registration_request, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if "result" in result:
                            print(f"✅ Successfully registered PostgreSQL agent: {result['result']}")
                            return True
                    
            return False
            
        except Exception as e:
            print(f"⚠️  Registration failed: {e}")
            return False
    
    async def start_agent_server(self):
        """Start the agent server"""
        print(f"🚀 Starting PostgreSQL Database Agent on port {self.agent_port}")
        
        # Initialize database
        db_ready = await self.init_database()
        if not db_ready:
            print("❌ Database initialization failed")
            return
        
        # Register with hub
        await self.register_with_hub()
        
        # Start server
        config = uvicorn.Config(
            self.app,
            host="localhost",
            port=self.agent_port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

async def main():
    """Main function to start the PostgreSQL database agent"""
    print("🐘 PostgreSQL Database Agent Starting...")
    print("=" * 50)
    
    # Check environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        print("❌ ANTHROPIC_API_KEY not found")
        return
    
    print(f"✅ ANTHROPIC_API_KEY loaded ({len(api_key)} chars)")
    
    # Create LLM
    try:
        llm = ChatAnthropic(
            model=os.getenv('LLM_MODEL', 'claude-3-haiku-20240307'),
            temperature=0.1,
            api_key=api_key
        )
        print("✅ Anthropic LLM configured")
    except Exception as e:
        print(f"❌ Failed to create LLM: {e}")
        return
    
    # Create and start agent
    hub_url = "http://localhost:5000/mcp"
    agent_port = 8002
    
    agent = PostgreSQLDatabaseAgent(llm, hub_url, agent_port)
    
    print("🤖 PostgreSQL Database Agent configured, starting server...")
    print("   Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        await agent.start_agent_server()
    except KeyboardInterrupt:
        print("\n⏹️  PostgreSQL Database Agent stopped by user")
    except Exception as e:
        print(f"❌ PostgreSQL Database Agent failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
