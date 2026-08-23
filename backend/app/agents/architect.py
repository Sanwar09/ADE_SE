import json
import re
import time
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState
from app.agents.context_builder import ContextBuilder


def architect_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Architect"

    file_store = state.get("file_store")
    twin = state.get("twin")
    user_story = state.get("user_story", "")

    context = ""
    if file_store and twin:
        cb = ContextBuilder(file_store, twin)
        context = cb.get_architect_context(user_story)

    system_instruction = (
        "You are an expert Software Architect.\n"
        "Analyze the provided context and the user's feature request / bug fix.\n"
        "Determine the exact files that must be modified and any new files that must be created.\n"
        "IMPORTANT RULES:\n"
        "1. Respect repository folder conventions (e.g. if adding a UI page/component/html, place it in frontend/ or client/; if adding an API endpoint/model, place it in backend/ or app/).\n"
        "2. For modified files, the path MUST match an existing file in the project file tree.\n"
        "3. Output ONLY a valid JSON object matching this schema:\n"
        "{\n"
        '  "summary": "High-level architecture design and rationale",\n'
        '  "files_to_create": [{"path": "exact/relative/path.ext", "description": "Purpose of this file"}],\n'
        '  "files_to_modify": [{"path": "exact/existing/path.ext", "description": "Reason for modification", "what_to_change": "Specific changes"}]\n'
        "}\n"
    )

    prompt = f"{context}\n\n=== USER REQUIREMENTS ===\n{user_story}\n\nGenerate the JSON architecture plan:"

    response = call_llm_safe(prompt, system_instruction=system_instruction, temperature=0.1)

    plan = None
    try:
        # Try finding json markdown fence
        if "```json" in response:
            json_str = response.split("```json")[1].split("```")[0].strip()
        elif "```" in response:
            json_str = response.split("```")[1].split("```")[0].strip()
        else:
            # Match first { to last }
            match = re.search(r"\{.*\}", response, re.DOTALL)
            json_str = match.group(0) if match else response.strip()

        plan = json.loads(json_str)
    except Exception:
        # Fallback plan if json parsing failed
        plan = {
            "summary": "Architecture plan for user request: " + user_story[:150],
            "files_to_create": [],
            "files_to_modify": [],
            "raw_response": response
        }

    # Ensure required keys exist
    if "files_to_create" not in plan:
        plan["files_to_create"] = []
    if "files_to_modify" not in plan:
        plan["files_to_modify"] = []

    state["architecture_plan"] = plan
    state["trajectory_logs"].append({
        "agent": "Architect",
        "timestamp": time.time(),
        "action": "Generated Architecture Plan",
        "output": json.dumps(plan, indent=2)
    })

    return state
