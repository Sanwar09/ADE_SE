from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    task_prompt: str
    repo_path: str
    current_agent: str
    trajectory_logs: List[Dict[str, Any]]
    
    file_store: Any
    twin: Any
    
    user_story: Optional[str]
    architecture_plan: Optional[Dict[str, Any]]
    security_report: Optional[str]
    generated_code: Optional[Dict[str, str]]
    original_code: Optional[Dict[str, str]]
    test_results: Optional[Dict[str, Any]]
    test_attempts: int
    review_verdict: Optional[str]
    devops_summary: Optional[str]
    status: str
