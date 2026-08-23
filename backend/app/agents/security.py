import time
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState


def security_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Security"

    architecture_plan = state.get("architecture_plan") or {}
    user_story = state.get("user_story", "")

    system_instruction = (
        "You are an Application Security Engineer (AppSec).\n"
        "Review the proposed architecture plan and user requirements for potential security vulnerabilities.\n"
        "Check for:\n"
        "- Injection risks (SQL, Command, XSS)\n"
        "- Insecure authentication, session management, or hardcoded secrets\n"
        "- Missing input validation or CORS misconfigurations\n"
        "Provide clear, actionable security requirements for the Developer agent."
    )

    # Extract only the summary from architecture plan to save tokens
    plan_summary = ""
    if isinstance(architecture_plan, dict):
        plan_summary = architecture_plan.get("summary", str(architecture_plan)[:2000])
    else:
        plan_summary = str(architecture_plan)[:2000]

    prompt = (
        f"=== USER STORY ===\n{user_story[:2000]}\n\n"
        f"=== ARCHITECTURE PLAN ===\n{plan_summary}\n\n"
        f"Provide your security review and developer guidelines:"
    )

    report = call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=2000)

    state["security_report"] = report
    state["trajectory_logs"].append({
        "agent": "Security",
        "timestamp": time.time(),
        "action": "Generated Security Assessment & Threat Model",
        "output": report
    })

    return state
