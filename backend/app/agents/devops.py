import time
from app.utils.llm import call_llm_safe
from app.utils.ci_cd_generator import CICDGenerator
from app.agents.state import AgentState


def devops_node(state: AgentState) -> AgentState:
    state["current_agent"] = "DevOps"

    generated_code = state.get("generated_code") or {}
    architecture_plan = state.get("architecture_plan") or {}
    file_store = state.get("file_store")

    # ── 1. Generate REAL CI/CD pipeline files ──
    cicd_files = {}
    try:
        cicd_files = CICDGenerator.generate_all(file_store, project_name="adt-se")
    except Exception as e:
        cicd_files = {".github/workflows/ci.yml": f"# CI/CD generation error: {e}"}

    # Merge CI/CD files into generated_code so they get written to disk
    for path, content in cicd_files.items():
        generated_code[path] = content

    state["generated_code"] = generated_code

    # ── 2. LLM-powered deployment assessment ──
    system_instruction = (
        "You are a Lead DevOps & Platform Engineer.\n"
        "Analyze the generated code and architecture changes to determine deployment impact:\n"
        "1. Check if any new dependencies were introduced (e.g. imports requiring requirements.txt or package.json updates)\n"
        "2. Review the generated CI/CD pipeline YAML for correctness\n"
        "3. Provide deployment instructions and release verification checklist.\n"
        "Keep your response concise (under 500 words)."
    )

    # Build a compact prompt to save tokens
    file_list = "\n".join(f"- {path}" for path in generated_code.keys())
    arch_summary = architecture_plan.get("summary", "") if isinstance(architecture_plan, dict) else ""

    prompt = (
        f"=== GENERATED FILES ===\n{file_list}\n\n"
        f"=== CI/CD PIPELINE GENERATED ===\n"
        f"Files: {', '.join(cicd_files.keys())}\n\n"
        f"=== ARCHITECTURE SUMMARY ===\n{arch_summary[:1000]}\n\n"
        f"Provide your concise DevOps Release & Deployment assessment:"
    )

    summary = call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=1500)

    state["devops_summary"] = summary
    state["status"] = "completed"

    cicd_list = ", ".join(cicd_files.keys())
    state["trajectory_logs"].append({
        "agent": "DevOps",
        "timestamp": time.time(),
        "action": f"Generated CI/CD Pipeline ({cicd_list}) & Deployment Assessment",
        "output": f"CI/CD Files Generated:\n{cicd_list}\n\n{summary}"
    })

    return state
