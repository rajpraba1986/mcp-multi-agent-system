"""
LangGraph Workflows for MCP Toolbox Integration.

This module provides sophisticated workflows using LangGraph for complex
multi-step database operations and analysis tasks.
"""

import logging
from typing import Dict, List, Optional, Any, TypedDict, Annotated
from datetime import datetime

from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.language_models import BaseLanguageModel
from langchain_openai import ChatOpenAI

from ..client.mcp_client import MCPToolboxClient
from ..client.langchain_tools import create_langchain_tools_sync
from .database_agent import DatabaseAgent


logger = logging.getLogger(__name__)


class WorkflowState(TypedDict):
    """State for workflow execution."""
    messages: Annotated[List[BaseMessage], "The messages in the conversation"]
    query: str
    current_step: str
    results: Dict[str, Any]
    error: Optional[str]
    intermediate_data: Dict[str, Any]


class DatabaseWorkflow:
    """
    A LangGraph workflow for complex database operations.
    
    This workflow can handle multi-step database queries, analysis,
    and reporting tasks by breaking them down into manageable steps.
    """
    
    def __init__(
        self,
        mcp_client: MCPToolboxClient,
        llm: Optional[BaseLanguageModel] = None,
        toolset_name: Optional[str] = None
    ):
        """
        Initialize the Database Workflow.
        
        Args:
            mcp_client: MCP Toolbox client instance
            llm: Language model to use
            toolset_name: Specific toolset to load
        """
        self.mcp_client = mcp_client
        self.toolset_name = toolset_name
        
        # Initialize LLM
        if llm is None:
            self.llm = ChatOpenAI(
                model="gpt-3.5-turbo",
                temperature=0.1
            )
        else:
            self.llm = llm
        
        # Load tools
        self.tools = create_langchain_tools_sync(mcp_client, toolset_name)
        self.tool_executor = ToolExecutor(self.tools)
        
        # Create the workflow graph
        self.workflow = self._create_workflow()
        
        logger.info("Initialized Database Workflow")
    
    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow."""
        workflow = StateGraph(WorkflowState)
        
        # Add nodes
        workflow.add_node("analyze_query", self._analyze_query)
        workflow.add_node("plan_execution", self._plan_execution)
        workflow.add_node("execute_step", self._execute_step)
        workflow.add_node("process_results", self._process_results)
        workflow.add_node("generate_response", self._generate_response)
        
        # Add edges
        workflow.set_entry_point("analyze_query")
        workflow.add_edge("analyze_query", "plan_execution")
        workflow.add_edge("plan_execution", "execute_step")
        workflow.add_conditional_edges(
            "execute_step",
            self._should_continue_execution,
            {
                "continue": "execute_step",
                "process": "process_results"
            }
        )
        workflow.add_edge("process_results", "generate_response")
        workflow.add_edge("generate_response", END)
        
        return workflow.compile()
    
    def _analyze_query(self, state: WorkflowState) -> WorkflowState:
        """Analyze the user query to understand intent."""
        try:
            query = state["query"]
            
            # Use LLM to analyze the query
            analysis_prompt = f"""
            Analyze this database query and determine:
            1. What type of operation is needed (search, analytics, reporting, etc.)
            2. What data entities are involved
            3. What specific information is being requested
            4. If multiple steps are needed
            
            Query: {query}
            
            Provide a structured analysis.
            """
            
            response = self.llm.invoke([HumanMessage(content=analysis_prompt)])
            
            state["current_step"] = "query_analyzed"
            state["intermediate_data"]["analysis"] = response.content
            state["messages"].append(response)
            
            logger.info("Query analysis completed")
            
        except Exception as e:
            logger.error(f"Error in query analysis: {e}")
            state["error"] = str(e)
        
        return state
    
    def _plan_execution(self, state: WorkflowState) -> WorkflowState:
        """Plan the execution steps based on the query analysis."""
        try:
            analysis = state["intermediate_data"].get("analysis", "")
            
            # Create execution plan
            planning_prompt = f"""
            Based on this query analysis, create a step-by-step execution plan:
            
            Analysis: {analysis}
            
            Available tools: {[tool.name for tool in self.tools]}
            
            Create a detailed plan with specific steps and tools to use.
            """
            
            response = self.llm.invoke([HumanMessage(content=planning_prompt)])
            
            state["current_step"] = "execution_planned"
            state["intermediate_data"]["execution_plan"] = response.content
            state["intermediate_data"]["step_count"] = 0
            state["intermediate_data"]["max_steps"] = 5  # Configurable
            state["messages"].append(response)
            
            logger.info("Execution planning completed")
            
        except Exception as e:
            logger.error(f"Error in execution planning: {e}")
            state["error"] = str(e)
        
        return state
    
    def _execute_step(self, state: WorkflowState) -> WorkflowState:
        """Execute a single step of the plan."""
        try:
            step_count = state["intermediate_data"]["step_count"]
            execution_plan = state["intermediate_data"]["execution_plan"]
            
            # Determine what to execute in this step
            step_prompt = f"""
            Execute step {step_count + 1} of this plan:
            
            Plan: {execution_plan}
            
            Based on the current step, determine:
            1. Which tool to use
            2. What parameters to pass
            3. What specific action to take
            
            Current step: {step_count + 1}
            """
            
            response = self.llm.invoke([HumanMessage(content=step_prompt)])
            
            # This is a simplified execution - in a real implementation,
            # you would parse the response and execute the appropriate tool
            
            state["intermediate_data"]["step_count"] += 1
            state["intermediate_data"][f"step_{step_count}_result"] = response.content
            state["messages"].append(response)
            
            logger.info(f"Executed step {step_count + 1}")
            
        except Exception as e:
            logger.error(f"Error in step execution: {e}")
            state["error"] = str(e)
        
        return state
    
    def _should_continue_execution(self, state: WorkflowState) -> str:
        """Determine whether to continue executing steps or process results."""
        step_count = state["intermediate_data"]["step_count"]
        max_steps = state["intermediate_data"]["max_steps"]
        
        if state.get("error") or step_count >= max_steps:
            return "process"
        
        # Check if execution is complete based on some criteria
        # This is simplified - you would implement more sophisticated logic
        return "process" if step_count >= 3 else "continue"
    
    def _process_results(self, state: WorkflowState) -> WorkflowState:
        """Process and consolidate results from all execution steps."""
        try:
            step_count = state["intermediate_data"]["step_count"]
            
            # Collect all step results
            step_results = []
            for i in range(step_count):
                result = state["intermediate_data"].get(f"step_{i}_result")
                if result:
                    step_results.append(result)
            
            # Process results
            processing_prompt = f"""
            Consolidate and process these execution results:
            
            Results: {step_results}
            
            Provide:
            1. A summary of what was accomplished
            2. Key findings or data
            3. Any insights or patterns discovered
            4. Recommendations for next steps
            """
            
            response = self.llm.invoke([HumanMessage(content=processing_prompt)])
            
            state["current_step"] = "results_processed"
            state["results"]["processed_results"] = response.content
            state["messages"].append(response)
            
            logger.info("Results processing completed")
            
        except Exception as e:
            logger.error(f"Error in results processing: {e}")
            state["error"] = str(e)
        
        return state
    
    def _generate_response(self, state: WorkflowState) -> WorkflowState:
        """Generate the final response to the user."""
        try:
            processed_results = state["results"].get("processed_results", "")
            original_query = state["query"]
            
            # Generate final response
            response_prompt = f"""
            Generate a comprehensive response to the user's original query:
            
            Original Query: {original_query}
            
            Processed Results: {processed_results}
            
            Create a clear, informative response that:
            1. Directly answers the user's question
            2. Provides relevant data and insights
            3. Explains the methodology used
            4. Suggests follow-up actions if appropriate
            """
            
            response = self.llm.invoke([HumanMessage(content=response_prompt)])
            
            state["current_step"] = "completed"
            state["results"]["final_response"] = response.content
            state["messages"].append(response)
            
            logger.info("Response generation completed")
            
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
            state["error"] = str(e)
        
        return state
    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        Execute the workflow for a given query.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict containing the workflow results
        """
        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "current_step": "initialized",
            "results": {},
            "error": None,
            "intermediate_data": {}
        }
        
        try:
            final_state = self.workflow.invoke(initial_state)
            
            return {
                "success": True,
                "response": final_state["results"].get("final_response", "No response generated"),
                "steps_executed": final_state["intermediate_data"].get("step_count", 0),
                "error": final_state.get("error"),
                "intermediate_data": final_state["intermediate_data"]
            }
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            return {
                "success": False,
                "response": f"Workflow execution failed: {str(e)}",
                "steps_executed": 0,
                "error": str(e),
                "intermediate_data": {}
            }


class AnalyticsWorkflow:
    """
    Specialized workflow for analytics and reporting tasks.
    """
    
    def __init__(
        self,
        mcp_client: MCPToolboxClient,
        llm: Optional[BaseLanguageModel] = None,
        toolset_name: str = "analytics"
    ):
        """
        Initialize the Analytics Workflow.
        
        Args:
            mcp_client: MCP Toolbox client instance
            llm: Language model to use
            toolset_name: Toolset for analytics tools
        """
        self.mcp_client = mcp_client
        self.database_agent = DatabaseAgent(mcp_client, llm, toolset_name)
        
        logger.info("Initialized Analytics Workflow")
    
    def run_sales_analysis(
        self,
        start_date: str,
        end_date: str,
        include_trends: bool = True
    ) -> Dict[str, Any]:
        """
        Run a comprehensive sales analysis.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            include_trends: Whether to include trend analysis
            
        Returns:
            Dict containing analysis results
        """
        query = f"""
        Perform a comprehensive sales analysis for the period from {start_date} to {end_date}.
        
        Include:
        1. Total sales summary
        2. Top-selling products
        3. Sales by category
        4. Daily/weekly trends if requested: {include_trends}
        5. Key insights and recommendations
        """
        
        return self.database_agent.analyze_data(query, include_visualizations=True)
    
    def run_customer_analysis(self, months_back: int = 12) -> Dict[str, Any]:
        """
        Run customer behavior analysis.
        
        Args:
            months_back: Number of months to analyze
            
        Returns:
            Dict containing customer analysis
        """
        query = f"""
        Analyze customer behavior and segments for the last {months_back} months.
        
        Include:
        1. Customer segmentation
        2. Purchase patterns
        3. Customer lifetime value insights
        4. Retention analysis
        5. Recommendations for customer engagement
        """
        
        return self.database_agent.analyze_data(query)
    
    def generate_executive_report(
        self,
        time_period: str = "last 30 days"
    ) -> Dict[str, Any]:
        """
        Generate an executive summary report.
        
        Args:
            time_period: Time period for the report
            
        Returns:
            Dict containing executive report
        """
        query = f"""
        Generate an executive summary report for {time_period}.
        
        Include:
        1. Key performance indicators (KPIs)
        2. Revenue and sales metrics
        3. Customer insights
        4. Operational highlights
        5. Areas of concern or opportunity
        6. Strategic recommendations
        
        Format this as an executive summary suitable for leadership review.
        """
        
        return self.database_agent.analyze_data(query)


class InteractiveWorkflow:
    """
    Interactive workflow that allows for multi-turn conversations
    and iterative refinement of queries.
    """
    
    def __init__(
        self,
        mcp_client: MCPToolboxClient,
        llm: Optional[BaseLanguageModel] = None,
        toolset_name: Optional[str] = None
    ):
        """
        Initialize the Interactive Workflow.
        
        Args:
            mcp_client: MCP Toolbox client instance
            llm: Language model to use
            toolset_name: Toolset to load
        """
        self.mcp_client = mcp_client
        self.database_agent = DatabaseAgent(mcp_client, llm, toolset_name)
        self.conversation_history = []
        
        logger.info("Initialized Interactive Workflow")
    
    def start_conversation(self, initial_query: str) -> Dict[str, Any]:
        """
        Start an interactive conversation.
        
        Args:
            initial_query: Initial user query
            
        Returns:
            Dict containing response and conversation state
        """
        self.conversation_history = []
        return self.continue_conversation(initial_query)
    
    def continue_conversation(self, user_input: str) -> Dict[str, Any]:
        """
        Continue the conversation with user input.
        
        Args:
            user_input: User's input/query
            
        Returns:
            Dict containing response and conversation state
        """
        # Add user input to history
        user_message = HumanMessage(content=user_input)
        self.conversation_history.append(user_message)
        
        # Get response from agent
        result = self.database_agent.query(user_input, self.conversation_history)
        
        # Add assistant response to history
        if result["success"]:
            ai_message = AIMessage(content=result["answer"])
            self.conversation_history.append(ai_message)
        
        return {
            "response": result["answer"],
            "success": result["success"],
            "error": result.get("error"),
            "conversation_length": len(self.conversation_history),
            "suggestions": self.database_agent.suggest_queries()
        }
    
    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation so far.
        
        Returns:
            String summary of the conversation
        """
        if not self.conversation_history:
            return "No conversation history."
        
        summary_query = """
        Summarize this conversation, highlighting:
        1. Key topics discussed
        2. Data insights discovered
        3. Actions taken
        4. Outstanding questions or next steps
        """
        
        result = self.database_agent.query(summary_query, self.conversation_history)
        return result["answer"]
    
    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []
        logger.info("Conversation history cleared")
