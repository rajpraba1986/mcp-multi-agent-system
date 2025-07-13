"""
Agent Orchestration Workflow Example.
Demonstrates how agents communicate via the MCP Hub for complex tasks.
"""

import asyncio
import logging
import aiohttp
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Orchestrates workflows between multiple agents via the MCP Hub.
    Shows how the system can be expanded with new agents.
    """
    
    def __init__(self, hub_url: str = "http://localhost:5000/mcp"):
        self.hub_url = hub_url
        self.orchestrator_id = f"orchestrator-{uuid.uuid4().hex[:8]}"
    
    async def web_extraction_and_notification_workflow(
        self, 
        url: str, 
        notify_email: str,
        extraction_type: str = "article"
    ) -> Dict[str, Any]:
        """
        Complete workflow: Extract web data → Store in DB → Send notification.
        Demonstrates A2A communication between Browserbase, Database, and Email agents.
        """
        workflow_id = f"workflow_{uuid.uuid4().hex[:8]}"
        results = {"workflow_id": workflow_id, "steps": []}
        
        try:
            # Step 1: Call Browserbase Agent to extract data
            logger.info(f"Step 1: Extracting data from {url}")
            browserbase_agent = await self._discover_agent("web_automation")
            
            if not browserbase_agent:
                raise Exception("Browserbase agent not available")
            
            extraction_result = await self._call_agent(
                browserbase_agent["endpoint_url"],
                "extract_website_data",
                {
                    "url": url,
                    "extraction_type": extraction_type,
                    "store_in_database": True,  # This triggers A2A call to Database agent
                    "send_notification": False  # We'll handle notification separately
                }
            )
            
            results["steps"].append({
                "step": 1,
                "action": "web_extraction",
                "status": "completed",
                "agent": "browserbase",
                "result": extraction_result
            })
            
            # Step 2: The Browserbase agent automatically stored data via A2A to Database agent
            # We can verify the storage by querying the Database agent
            logger.info("Step 2: Verifying data storage")
            database_agent = await self._discover_agent("data_storage")
            
            if database_agent:
                verification_result = await self._call_agent(
                    database_agent["endpoint_url"],
                    "query_data",
                    {
                        "question": f"Show me the most recent extraction from {url}"
                    }
                )
                
                results["steps"].append({
                    "step": 2,
                    "action": "data_verification",
                    "status": "completed",
                    "agent": "database",
                    "result": verification_result
                })
            
            # Step 3: Send notification email about the extraction
            logger.info("Step 3: Sending notification email")
            email_agent = await self._discover_agent("communication")
            
            if email_agent:
                notification_result = await self._call_agent(
                    email_agent["endpoint_url"],
                    "send_notification",
                    {
                        "recipient": notify_email,
                        "subject": f"Web Extraction Complete: {url}",
                        "body": f"""
                        Web extraction workflow completed successfully.
                        
                        URL: {url}
                        Type: {extraction_type}
                        Workflow ID: {workflow_id}
                        
                        The extracted data has been stored in the database and is ready for analysis.
                        """,
                        "priority": "normal"
                    }
                )
                
                results["steps"].append({
                    "step": 3,
                    "action": "notification",
                    "status": "completed",
                    "agent": "email",
                    "result": notification_result
                })
            
            results["status"] = "completed"
            results["message"] = "Workflow completed successfully"
            
        except Exception as e:
            logger.error(f"Workflow error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results
    
    async def data_analysis_workflow(
        self,
        analysis_request: str,
        notify_email: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Data analysis workflow: Query data → Analyze → Optionally notify.
        """
        workflow_id = f"analysis_{uuid.uuid4().hex[:8]}"
        results = {"workflow_id": workflow_id, "steps": []}
        
        try:
            # Step 1: Perform data analysis
            logger.info(f"Step 1: Analyzing data: {analysis_request}")
            database_agent = await self._discover_agent("data_storage")
            
            if not database_agent:
                raise Exception("Database agent not available")
            
            analysis_result = await self._call_agent(
                database_agent["endpoint_url"],
                "analyze_data",
                {
                    "analysis_request": analysis_request,
                    "include_visualizations": True
                }
            )
            
            results["steps"].append({
                "step": 1,
                "action": "data_analysis",
                "status": "completed",
                "agent": "database",
                "result": analysis_result
            })
            
            # Step 2: Send analysis results via email (if requested)
            if notify_email:
                logger.info("Step 2: Sending analysis results")
                email_agent = await self._discover_agent("communication")
                
                if email_agent:
                    notification_result = await self._call_agent(
                        email_agent["endpoint_url"],
                        "send_notification",
                        {
                            "recipient": notify_email,
                            "subject": f"Data Analysis Complete: {analysis_request[:50]}...",
                            "body": f"""
                            Data analysis completed.
                            
                            Request: {analysis_request}
                            Workflow ID: {workflow_id}
                            
                            Results: {analysis_result.get('answer', 'No results')}
                            """,
                            "priority": "normal"
                        }
                    )
                    
                    results["steps"].append({
                        "step": 2,
                        "action": "notification",
                        "status": "completed",
                        "agent": "email",
                        "result": notification_result
                    })
            
            results["status"] = "completed"
            results["message"] = "Analysis workflow completed successfully"
            
        except Exception as e:
            logger.error(f"Analysis workflow error: {e}")
            results["status"] = "failed"
            results["error"] = str(e)
        
        return results
    
    async def _discover_agent(self, agent_type: str) -> Optional[Dict[str, Any]]:
        """Discover an agent by type via the MCP Hub."""
        try:
            discovery_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "agents/discover",
                "params": {
                    "agent_type": agent_type
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.hub_url,
                    json=discovery_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        agents = result.get("result", {}).get("agents", [])
                        return agents[0] if agents else None
            
            return None
        
        except Exception as e:
            logger.error(f"Agent discovery error: {e}")
            return None
    
    async def _call_agent(
        self, 
        agent_endpoint: str, 
        method: str, 
        params: Dict[str, Any]
    ) -> Any:
        """Make an A2A call to another agent."""
        try:
            request_data = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": method,
                "params": params
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    agent_endpoint,
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result.get("result")
                    else:
                        logger.error(f"Agent call failed: {response.status}")
                        return None
        
        except Exception as e:
            logger.error(f"Agent call error: {e}")
            return None


# Example usage showing how to run complex workflows
async def main():
    """Example of running agent workflows."""
    
    # Initialize orchestrator
    orchestrator = AgentOrchestrator()
    
    # Example 1: Web extraction and notification workflow
    print("🚀 Starting web extraction workflow...")
    result1 = await orchestrator.web_extraction_and_notification_workflow(
        url="https://example.com/article",
        notify_email="user@example.com",
        extraction_type="article"
    )
    print(f"✅ Workflow 1 result: {result1['status']}")
    
    # Example 2: Data analysis workflow
    print("📊 Starting data analysis workflow...")
    result2 = await orchestrator.data_analysis_workflow(
        analysis_request="Analyze all web extractions from the last week and identify trending topics",
        notify_email="analyst@example.com"
    )
    print(f"✅ Workflow 2 result: {result2['status']}")


if __name__ == "__main__":
    asyncio.run(main())
