import re
import time
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState
from app.agents.context_builder import ContextBuilder


def developer_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Developer"

    file_store = state.get("file_store")
    twin = state.get("twin")
    user_story = state.get("user_story", "")
    architecture_plan = state.get("architecture_plan") or {}
    security_report = state.get("security_report", "")
    test_results = state.get("test_results")
    review_verdict = state.get("review_verdict")

    files_to_modify = []
    files_to_create = []

    if isinstance(architecture_plan, dict):
        for f in architecture_plan.get("files_to_modify", []):
            p = f["path"] if isinstance(f, dict) and "path" in f else str(f)
            files_to_modify.append(p)
        for f in architecture_plan.get("files_to_create", []):
            p = f["path"] if isinstance(f, dict) and "path" in f else str(f)
            files_to_create.append(p)

    context = ""
    if file_store and twin:
        cb = ContextBuilder(file_store, twin)
        context = cb.get_developer_context(user_story, files_to_modify, files_to_create)

    # Capture original code for modified files
    original_code = {}
    if file_store:
        for path in files_to_modify:
            content = file_store.get_file(path)
            if content is not None:
                original_code[path] = content
            else:
                # Try normalized path
                norm_path = path.replace("/", "\\") if "/" in path else path.replace("\\", "/")
                content = file_store.get_file(norm_path)
                if content is not None:
                    original_code[path] = content
    state["original_code"] = original_code

    system_instruction = (
        "You are an elite Senior Full-Stack Developer. "
        "Your task is to write complete, production-ready code for the requested files. "
        "CRITICAL RULES:\n"
        "1. Place files in the EXACT correct repository folders (e.g. frontend files in frontend/, backend files in backend/).\n"
        "2. For modified files, output the COMPLETE updated file content (NEVER use placeholders or comments like '... existing code ...').\n"
        "3. For new files, output the COMPLETE new file content with all imports, functions, and styles.\n"
        "4. Wrap EVERY file in this exact delimiter format:\n\n"
        "=== FILE: exact/relative/path/to/file.ext ===\n"
        "<complete file content here>\n"
        "=== END FILE ===\n\n"
    )

    prompt = (
        f"{context}\n\n"
        f"=== USER STORY & REQUIREMENTS ===\n{user_story}\n\n"
        f"=== ARCHITECTURE PLAN ===\n{architecture_plan}\n\n"
        f"=== SECURITY GUIDELINES ===\n{security_report}\n\n"
    )

    if test_results:
        prompt += f"=== PREVIOUS TEST RESULTS (FIX THESE ISSUES) ===\n{test_results}\n\n"
    if review_verdict:
        prompt += f"=== PREVIOUS CODE REVIEW FEEDBACK (FIX THESE ISSUES) ===\n{review_verdict}\n\n"

    prompt += (
        "Generate all required files now using the delimiter format:\n"
        "=== FILE: path ===\n"
        "<code>\n"
        "=== END FILE ==="
    )

    response = call_llm_safe(prompt, system_instruction=system_instruction, temperature=0.1, max_tokens=8192)

    generated_code = {}

    # Primary parser: === FILE: path === ... === END FILE ===
    pattern = re.compile(r"===\s*FILE:\s*(.+?)\s*===\s*\n(.*?)\n===\s*END FILE\s*===", re.DOTALL)
    matches = pattern.findall(response)

    for path, content in matches:
        clean_path = path.strip().replace('"', '').replace("'", "")
        generated_code[clean_path] = content.strip()

    # Fallback 1: Match ```language:path or ```path
    if not generated_code:
        fence_pattern = re.compile(r"```(?:[a-zA-Z0-9_-]+[:\s]+)?([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9]+)\n(.*?)```", re.DOTALL)
        fence_matches = fence_pattern.findall(response)
        for path, content in fence_matches:
            clean_path = path.strip()
            if "/" in clean_path or "\\" in clean_path or "." in clean_path:
                generated_code[clean_path] = content.strip()

    # Fallback 2: If code block without file name, match with planned files
    if not generated_code and (files_to_create or files_to_modify):
        all_targets = files_to_create + files_to_modify
        blocks = re.findall(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", response, re.DOTALL)
        for i, block in enumerate(blocks):
            if i < len(all_targets):
                generated_code[all_targets[i]] = block.strip()

    # Fallback 3: If no code blocks at all, make sure response is captured
    if not generated_code and files_to_create:
        generated_code[files_to_create[0]] = response.strip()

    state["generated_code"] = generated_code

    file_list_str = "\n".join(f"- {p} ({len(c.splitlines())} lines)" for p, c in generated_code.items())
    log_content = f"Successfully generated {len(generated_code)} file(s):\n{file_list_str}" if generated_code else "Completed generation phase."

    state["trajectory_logs"].append({
        "agent": "Developer",
        "timestamp": time.time(),
        "action": "Generated Source Code",
        "output": log_content
    })

    return state
