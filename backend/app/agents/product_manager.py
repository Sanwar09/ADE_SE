import time
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState


def pm_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Product Manager"

    file_store = state.get("file_store")
    task_prompt = state.get("task_prompt", "")

    project_overview = "Project Overview:\n"
    if file_store:
        project_overview += "File Tree:\n" + file_store.get_file_tree() + "\n\n"
        project_overview += "Key Files:\n"
        for path, content in list(file_store.get_key_files().items())[:3]:
            project_overview += f"--- {path} ---\n{content[:1500]}\n\n"

    system_instruction = (
        "You are an expert Agile Product Manager and Business Analyst.\n"
        "Analyze the user's task request and the existing project structure.\n"
        "Generate a detailed technical specification including:\n"
        "1. User Story with business context and acceptance criteria\n"
        "2. Scope boundaries and constraints\n"
        "3. Expected edge cases and non-functional requirements"
    )

    prompt = f"{project_overview}\nUser Task:\n{task_prompt}\n\nPlease generate the detailed user story and acceptance criteria."

    user_story = call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=2500)

    state["user_story"] = user_story
    state["trajectory_logs"].append({
        "agent": "Product Manager",
        "timestamp": time.time(),
        "action": "Generated Technical Specifications & Acceptance Criteria",
        "output": user_story
    })

    return state
