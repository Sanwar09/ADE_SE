"""
GitHub REST API Client — GitHub integration for Push, Fork, Pull Request, and Direct Deploy.
Supports:
  1. Personal / Contributor Mode: Direct push & CI/CD trigger on main/branch.
  2. Industry / Team Mode: Feature branch -> Push -> Pull Request with 7-Agent SDLC Report.
  3. Fork Workflow: 1-click fork external company repo -> Push to fork -> Cross-fork PR to team lead.
"""

import os
import re
import time
from typing import Dict, Any, Optional, List

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False


GITHUB_API = "https://api.github.com"
USER_AGENT = "ADT-SE-Platform/2.0"

# Runtime token storage (can be set from UI settings panel)
_runtime_token: Optional[str] = None


def set_token(token: str):
    """Set GitHub token at runtime (from UI settings panel)."""
    global _runtime_token
    _runtime_token = token.strip() if token and token.strip() else None


def _get_token() -> Optional[str]:
    """Get GitHub PAT from runtime config or environment."""
    if _runtime_token:
        return _runtime_token
    token = os.getenv("GITHUB_TOKEN", "")
    if token and token != "your_github_token_here":
        return token
    return None


def is_configured() -> bool:
    """Check if GitHub integration is available."""
    return HAS_HTTPX and _get_token() is not None


def _headers() -> Dict[str, str]:
    token = _get_token()
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def extract_owner_repo(remote_url: str) -> Optional[Dict[str, str]]:
    """Extract owner and repo name from a git remote URL."""
    if not remote_url:
        return None
    patterns = [
        r"github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?/?$",
        r"github\.com/([^/]+)/([^/.]+?)(?:\.git)?/?$",
    ]
    for pattern in patterns:
        match = re.search(pattern, remote_url.strip())
        if match:
            return {"owner": match.group(1), "repo": match.group(2)}
    return None


def get_authenticated_user() -> Dict[str, Any]:
    """Get the currently authenticated GitHub user."""
    if not is_configured():
        return {"status": "error", "error": "GitHub not configured"}
    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"{GITHUB_API}/user", headers=_headers())
            if r.status_code == 401:
                return {"status": "error", "error": "Invalid GitHub token. Please verify token permissions."}
            r.raise_for_status()
            data = r.json()
            return {
                "status": "success",
                "username": data.get("login"),
                "name": data.get("name"),
                "avatar_url": data.get("avatar_url"),
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def get_repo_info(owner: str, repo: str) -> Dict[str, Any]:
    """Get repository information and push permissions from GitHub API."""
    if not is_configured():
        # Even without token, public info can be fetched
        try:
            with httpx.Client(timeout=15) as client:
                r = client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers={"User-Agent": USER_AGENT})
                if r.status_code == 200:
                    data = r.json()
                    return {
                        "status": "success",
                        "name": data.get("full_name"),
                        "default_branch": data.get("default_branch", "main"),
                        "private": data.get("private", False),
                        "html_url": data.get("html_url"),
                        "can_push": False,
                        "is_fork": data.get("fork", False),
                        "parent": data.get("parent", {}).get("full_name") if data.get("fork") else None,
                    }
        except Exception:
            pass
        return {"status": "error", "error": "GitHub token not configured."}

    try:
        with httpx.Client(timeout=15) as client:
            r = client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=_headers())
            if r.status_code == 404:
                return {
                    "status": "error",
                    "error": f"Repository '{owner}/{repo}' not found or your token lacks access."
                }
            r.raise_for_status()
            data = r.json()

            permissions = data.get("permissions", {})
            can_push = permissions.get("push", False) or permissions.get("admin", False)

            return {
                "status": "success",
                "name": data.get("full_name"),
                "default_branch": data.get("default_branch", "main"),
                "private": data.get("private", False),
                "html_url": data.get("html_url"),
                "can_push": can_push,
                "is_fork": data.get("fork", False),
                "parent": data.get("parent", {}).get("full_name") if data.get("fork") else None,
                "parent_clone_url": data.get("parent", {}).get("clone_url") if data.get("fork") else None,
            }
    except Exception as e:
        return {"status": "error", "error": str(e)}


def check_write_access(owner: str, repo: str) -> bool:
    """Check if the authenticated user has write (push) access to the repo."""
    info = get_repo_info(owner, repo)
    return info.get("can_push", False)


def fork_repo(owner: str, repo: str) -> Dict[str, Any]:
    """
    Fork a repository to the authenticated user's account.
    First checks if the user ALREADY has a fork of this repo.
    """
    if not is_configured():
        return {"status": "error", "error": "GitHub token not configured. Please connect GitHub in the top bar."}

    user_res = get_authenticated_user()
    current_user = user_res.get("username") if user_res.get("status") == "success" else None

    # Step 1: If current user is the owner, no need to fork!
    if current_user and current_user.lower() == owner.lower():
        return {
            "status": "success",
            "is_owner": True,
            "fork_full_name": f"{owner}/{repo}",
            "fork_clone_url": f"https://github.com/{owner}/{repo}.git",
            "owner": owner,
            "message": f"You are the owner of {owner}/{repo}. Direct push & PR available!",
        }

    # Step 2: Check if user already has an existing fork of this repo
    if current_user:
        try:
            with httpx.Client(timeout=15) as client:
                check_r = client.get(f"{GITHUB_API}/repos/{current_user}/{repo}", headers=_headers())
                if check_r.status_code == 200:
                    data = check_r.json()
                    return {
                        "status": "success",
                        "already_exists": True,
                        "fork_full_name": data.get("full_name"),
                        "fork_url": data.get("html_url"),
                        "fork_clone_url": data.get("clone_url"),
                        "fork_ssh_url": data.get("ssh_url"),
                        "owner": current_user,
                        "message": f"Linked to your existing fork @{data.get('full_name')}!",
                    }
        except Exception:
            pass

    # Step 3: Trigger GitHub API Fork creation
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/forks",
                headers=_headers(),
                json={"default_branch_only": False},
            )

            # 202 Accepted (fork is queued/in-progress) or 200/201 OK
            if r.status_code in [200, 201, 202]:
                data = r.json()
                fork_owner = data.get("owner", {}).get("login", current_user or "you")
                return {
                    "status": "success",
                    "fork_full_name": data.get("full_name", f"{fork_owner}/{repo}"),
                    "fork_url": data.get("html_url", f"https://github.com/{fork_owner}/{repo}"),
                    "fork_clone_url": data.get("clone_url", f"https://github.com/{fork_owner}/{repo}.git"),
                    "fork_ssh_url": data.get("ssh_url"),
                    "owner": fork_owner,
                    "message": f"Successfully forked {owner}/{repo} to @{fork_owner}/{repo}!",
                }
            elif r.status_code == 404:
                return {
                    "status": "error",
                    "error": (
                        f"Could not fork '{owner}/{repo}'. Ensure your GitHub Personal Access Token has 'repo' scope "
                        "and that the repository is accessible. (You can also deploy directly if you have contributor access)."
                    )
                }
            else:
                body = r.json() if r.content else {}
                err_msg = body.get("message", f"GitHub returned status {r.status_code}")
                return {"status": "error", "error": err_msg}

    except Exception as e:
        return {"status": "error", "error": str(e)}


def create_pull_request(
    owner: str,
    repo: str,
    title: str,
    body: str,
    head_branch: str,
    base_branch: str = "main",
    head_repo_owner: str = "",
) -> Dict[str, Any]:
    """
    Create a Pull Request on GitHub.
    Supports:
      - Internal PR: head_branch in the same repo
      - Cross-fork PR: head_branch formatted as 'fork_owner:feature-branch'
    """
    if not is_configured():
        return {"status": "error", "error": "GitHub token not configured"}
    try:
        head = head_branch
        # For cross-fork PRs: head must be 'username:branch'
        if head_repo_owner and head_repo_owner.lower() != owner.lower():
            head = f"{head_repo_owner}:{head_branch}"

        with httpx.Client(timeout=15) as client:
            r = client.post(
                f"{GITHUB_API}/repos/{owner}/{repo}/pulls",
                headers=_headers(),
                json={
                    "title": title,
                    "body": body,
                    "head": head,
                    "base": base_branch,
                },
            )

            if r.status_code in [200, 201]:
                data = r.json()
                return {
                    "status": "success",
                    "pr_number": data.get("number"),
                    "pr_url": data.get("html_url"),
                    "title": data.get("title"),
                    "target_repo": f"{owner}/{repo}",
                    "message": f"PR #{data.get('number')} created on {owner}/{repo}!",
                }
            else:
                error_body = r.json() if r.content else {}
                msg = error_body.get("message", f"HTTP {r.status_code}")
                errors = error_body.get("errors", [])
                if errors and isinstance(errors, list):
                    details = "; ".join(e.get("message", str(e)) for e in errors if isinstance(e, dict))
                    if details:
                        msg += f": {details}"
                return {"status": "error", "error": msg}

    except Exception as e:
        return {"status": "error", "error": str(e)}


def generate_pr_body(
    task_prompt: str,
    trajectory_logs: List[Dict] = None,
    generated_files: List[str] = None,
    test_results: Dict = None,
    review_verdict: str = None,
    devops_summary: str = None,
) -> str:
    """
    Generate a comprehensive, professional PR description from the 7-Agent SDLC output.
    """
    body = f"""## 🤖 ADT-SE: Autonomous SDLC Feature Pull Request

### 📋 Task Objective
> {task_prompt}

---

### 🚀 Summary of Changes Generated by 7 Multi-Agent Society
"""
    if generated_files:
        body += "#### 📁 Modified & Created Files:\n"
        for f in generated_files:
            tag = "CI/CD" if (".github" in f or "Dockerfile" in f or "docker-compose" in f) else "Source Code"
            body += f"- `{f}` *({tag})*\n"
        body += "\n"

    if test_results:
        passed = test_results.get("passed", True)
        badge = "✅ PASSED" if passed else "⚠️ NEEDS ATTENTION"
        body += f"#### 🧪 QA Automated Verification: {badge}\n"
        output_txt = test_results.get("output", "")
        if output_txt:
            body += f"```text\n{output_txt[:400]}\n```\n\n"

    if review_verdict:
        body += f"#### 🔍 Staff Code Review Assessment:\n"
        body += f"> {review_verdict[:400]}\n\n"

    if devops_summary:
        body += f"#### ⚙️ CI/CD & Deployment Strategy:\n"
        body += f"{devops_summary[:400]}\n\n"

    body += """---
*Autonomous SDLC Pipeline executed via [ADT-SE](https://github.com)*
*7-Agent Society: PM → Architect → Security → Developer → Tester → Reviewer → DevOps*
"""
    return body
