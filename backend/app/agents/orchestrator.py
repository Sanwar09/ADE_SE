from langgraph.graph import StateGraph, END
from app.agents.state import AgentState
from app.agents.product_manager import pm_node
from app.agents.architect import architect_node
from app.agents.security import security_node
from app.agents.developer import developer_node
from app.agents.tester import tester_node
from app.agents.reviewer import reviewer_node
from app.agents.devops import devops_node

def should_retry_developer(state: AgentState):
    if state.get("status") == "review_failed" and state.get("test_attempts", 0) < 3:
        return "developer"
    if not state.get("test_results", {}).get("passed", True) and state.get("test_attempts", 0) < 3:
        return "developer"
    return "devops"

def build_orchestrator():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("pm", pm_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("security", security_node)
    workflow.add_node("developer", developer_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("reviewer", reviewer_node)
    workflow.add_node("devops", devops_node)
    
    workflow.set_entry_point("pm")
    
    workflow.add_edge("pm", "architect")
    workflow.add_edge("architect", "security")
    workflow.add_edge("security", "developer")
    workflow.add_edge("developer", "tester")
    workflow.add_edge("tester", "reviewer")
    
    workflow.add_conditional_edges(
        "reviewer",
        should_retry_developer,
        {
            "developer": "developer",
            "devops": "devops"
        }
    )
    
    workflow.add_edge("devops", END)
    
    return workflow.compile()
