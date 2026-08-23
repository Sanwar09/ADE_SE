import time
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState


def reviewer_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Reviewer"

    original_code = state.get("original_code") or {}
    generated_code = state.get("generated_code") or {}
    user_story = state.get("user_story", "")
    test_results = state.get("test_results") or {}

    system_instruction = (
        "You are an elite Senior Staff Engineer conducting a strict Pull Request Code Review.\n"
        "Review the generated code against requirements, architecture standards, and test results.\n"
        "Check for:\n"
        "- Clean code architecture and proper abstractions\n"
        "- Error handling and edge cases\n"
        "- Correct folder placement and naming conventions\n"
        "Start your response with either 'VERDICT: PASS' or 'VERDICT: REVISE', followed by specific line-by-line feedback."
    )

    prompt = (
        f"=== USER REQUIREMENTS ===\n{user_story}\n\n"
        f"=== TEST STATUS ===\nPassed: {test_results.get('passed', True)}\nDetails: {test_results.get('output', '')}\n\n"
    )

    prompt += "=== GENERATED CODE ===\n"
    for path, content in generated_code.items():
        prompt += f"--- {path} ---\n{content[:4000]}\n\n"

    verdict = call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=2500)

    state["review_verdict"] = verdict

    if "VERDICT: PASS" in verdict.upper() or test_results.get("passed", True):
        state["status"] = "review_passed"
    else:
        state["status"] = "review_failed"  # Triggers retry loop back to Developer agent

    state["trajectory_logs"].append({
        "agent": "Reviewer",
        "timestamp": time.time(),
        "action": "Conducted Senior Code Review & PR Approval",
        "output": verdict
    })

    return state
