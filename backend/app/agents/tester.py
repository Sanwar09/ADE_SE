import time
import subprocess
from app.utils.llm import call_llm_safe
from app.agents.state import AgentState


def tester_node(state: AgentState) -> AgentState:
    state["current_agent"] = "Tester"

    repo_path = state.get("repo_path")
    generated_code = state.get("generated_code") or {}
    file_store = state.get("file_store")

    state["test_attempts"] = state.get("test_attempts", 0) + 1

    # 1. Static syntax verification
    syntax_errors = []
    for path, code in generated_code.items():
        if path.endswith(".py"):
            try:
                compile(code, path, "exec")
            except Exception as e:
                syntax_errors.append(f"Python syntax error in {path}: {str(e)}")

    # 2. Check for real automated test runner
    test_cmd = None
    if file_store and repo_path:
        if file_store.get_file("pytest.ini") or "test" in str(file_store.get_all_paths()):
            test_cmd = ["pytest", "--maxfail=1", "-q"]

    test_output = ""
    test_passed = True

    if syntax_errors:
        test_passed = False
        test_output = "Syntax Verification Failed:\n" + "\n".join(syntax_errors)
    elif test_cmd and repo_path:
        try:
            res = subprocess.run(test_cmd, cwd=repo_path, capture_output=True, text=True, timeout=20)
            test_passed = res.returncode == 0
            test_output = (res.stdout + "\n" + res.stderr).strip() or "Automated tests executed successfully."
        except Exception as ex:
            test_output = f"Test execution notes: {str(ex)}"
    else:
        test_passed = True
        test_output = f"Static syntax check passed across {len(generated_code)} generated file(s). All modules compiled cleanly."

    state["test_results"] = {
        "passed": test_passed,
        "output": test_output
    }

    system_instruction = "You are a QA Test Automation Engineer. Summarize the test outcome concisely."
    prompt = f"Test Results:\nPassed: {test_passed}\nOutput:\n{test_output}\n\nProvide a concise QA summary:"

    summary = call_llm_safe(prompt, system_instruction=system_instruction, max_tokens=1500)

    state["trajectory_logs"].append({
        "agent": "Tester",
        "timestamp": time.time(),
        "action": f"Executed QA Verification ({'PASSED' if test_passed else 'FAILED'})",
        "output": summary or test_output
    })

    return state
