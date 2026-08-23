import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.twin.scanner import RepositoryScanner
from app.twin.graph_builder import RepositoryDigitalTwin
from app.twin.file_store import FileStore
from app.twin.git_manager import GitManager

router = APIRouter(prefix="/api/twin", tags=["Digital Twin"])

# Global in-memory cache for active Digital Twin and FileStore
ACTIVE_TWIN: Optional[RepositoryDigitalTwin] = None
ACTIVE_FILE_STORE: Optional[FileStore] = None


class ScanRequest(BaseModel):
    repo_path: str


class CloneRequest(BaseModel):
    github_url: str


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


class ImpactRequest(BaseModel):
    target_nodes: List[str]
    depth: Optional[int] = 2


class GitCommitRequest(BaseModel):
    message: str = "Apply autonomous SDLC changes via ADT-SE"


@router.post("/scan")
def scan_repository(req: ScanRequest):
    """Scan a local directory — builds Digital Twin graph AND FileStore content index."""
    global ACTIVE_TWIN, ACTIVE_FILE_STORE
    try:
        repo_path = os.path.abspath(req.repo_path)
        if not os.path.exists(repo_path):
            raise HTTPException(status_code=400, detail=f"Path does not exist: {repo_path}")

        scanner = RepositoryScanner(repo_path)
        ACTIVE_TWIN, ACTIVE_FILE_STORE = scanner.scan()

        meta = dict(ACTIVE_TWIN.metadata)
        meta["languages"] = list(meta.get("languages", set()))

        return {
            "status": "success",
            "message": f"Digital Twin built for {repo_path}",
            "metadata": meta,
            "total_indexed_files": len(ACTIVE_FILE_STORE.files)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clone")
def clone_repository(req: CloneRequest):
    """Clone a GitHub repo, then scan it."""
    global ACTIVE_TWIN, ACTIVE_FILE_STORE
    try:
        repo_path = GitManager.clone(req.github_url)

        scanner = RepositoryScanner(repo_path)
        ACTIVE_TWIN, ACTIVE_FILE_STORE = scanner.scan()

        meta = dict(ACTIVE_TWIN.metadata)
        meta["languages"] = list(meta.get("languages", set()))

        return {
            "status": "success",
            "message": f"Cloned and scanned: {req.github_url}",
            "repo_path": repo_path,
            "metadata": meta,
            "total_indexed_files": len(ACTIVE_FILE_STORE.files)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
def search_codebase(req: SearchRequest):
    """Semantic search across the codebase using ChromaDB embeddings."""
    if not ACTIVE_FILE_STORE:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    results = ACTIVE_FILE_STORE.search(req.query, top_k=req.top_k)
    return {"status": "success", "results": results}


@router.get("/file")
def get_file_content(path: str):
    """Get the full content of a specific file."""
    if not ACTIVE_FILE_STORE:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    content = ACTIVE_FILE_STORE.get_file(path)
    if content is None:
        # Try alternate path separators
        norm = path.replace("/", "\\") if "/" in path else path.replace("\\", "/")
        content = ACTIVE_FILE_STORE.get_file(norm)
    if content is None:
        raise HTTPException(status_code=404, detail=f"File not found: {path}")
    return {"path": path, "content": content}


@router.get("/tree")
def get_file_tree():
    """Get the formatted directory tree of the scanned repository."""
    if not ACTIVE_FILE_STORE:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    return {"tree": ACTIVE_FILE_STORE.get_file_tree()}


@router.get("/graph")
def get_twin_graph():
    """Get the full Code Property Graph in Cytoscape JSON format."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    return {"status": "success", "elements": ACTIVE_TWIN.to_cytoscape_json()}


@router.post("/impact")
def analyze_impact(req: ImpactRequest):
    """Analyze the impact of changes to specific nodes in the graph."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    impact_data = ACTIVE_TWIN.get_impact_subgraph(req.target_nodes, depth=req.depth or 2)
    return {"status": "success", "impact_analysis": impact_data}


@router.get("/metadata")
def get_metadata():
    """Get current Digital Twin metadata and status."""
    if not ACTIVE_TWIN:
        return {"status": "inactive", "message": "No repository scanned yet."}
    meta = dict(ACTIVE_TWIN.metadata)
    meta["languages"] = list(meta.get("languages", set()))
    git_info = GitManager.get_repo_git_info(ACTIVE_TWIN.repo_path)
    return {
        "status": "active",
        "metadata": meta,
        "indexed_files": len(ACTIVE_FILE_STORE.files) if ACTIVE_FILE_STORE else 0,
        "git_info": git_info
    }


@router.post("/git/commit")
def commit_repository(req: GitCommitRequest):
    """Create a git commit with the latest staged / modified changes."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    res = GitManager.commit_changes(ACTIVE_TWIN.repo_path, req.message)
    return res


class GitPushRequest(BaseModel):
    branch: str = ""
    remote: str = "origin"


class GitBranchRequest(BaseModel):
    branch_name: str = ""


class GitPRRequest(BaseModel):
    title: str = "Autonomous SDLC Update via ADT-SE"
    body: str = "Auto-generated code changes from the 7-Agent SDLC pipeline."
    head_branch: str = ""
    base_branch: str = "main"


@router.post("/git/push")
def push_to_remote(req: GitPushRequest):
    """
    USER-INITIATED: Push current branch to remote.
    Requires git credentials or GITHUB_TOKEN in .env.
    """
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    res = GitManager.push_to_remote(ACTIVE_TWIN.repo_path, req.branch, req.remote)
    return res


@router.post("/git/branch")
def create_branch(req: GitBranchRequest):
    """Create and checkout a new feature branch."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    res = GitManager.create_branch(ACTIVE_TWIN.repo_path, req.branch_name)
    return res


@router.get("/git/diff")
def get_diff():
    """Get current git diff (staged + unstaged + untracked)."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    return GitManager.get_diff(ACTIVE_TWIN.repo_path)


@router.post("/git/pr")
def create_pull_request_endpoint(req: GitPRRequest):
    """
    USER-INITIATED: Create a Pull Request on GitHub.

    Supports TWO workflows:
    1. Direct push: User has write access -> push to same repo -> PR within repo
    2. Fork workflow: User forked the repo -> push to fork -> cross-fork PR to original

    This is the key industrial feature:
      Fresher gets company repo -> ADT-SE generates changes ->
      Fresher pushes to their fork -> Opens PR to company repo ->
      Team lead reviews and merges
    """
    global ACTIVE_TWIN, ACTIVE_FILE_STORE
    if not ACTIVE_TWIN:
        # Auto-recover from default workspace if available
        for candidate in ["c:/Final Year/workspace/Doclarity", "c:/Final Year"]:
            if os.path.exists(candidate):
                try:
                    scanner = RepositoryScanner(candidate)
                    ACTIVE_TWIN, ACTIVE_FILE_STORE = scanner.scan()
                    break
                except Exception:
                    pass
        if not ACTIVE_TWIN:
            raise HTTPException(status_code=404, detail="No repository scanned yet. Please scan your repository first.")

    from app.utils.github_api import (
        is_configured, extract_owner_repo,
        create_pull_request as gh_create_pr,
        generate_pr_body, get_repo_info, get_authenticated_user
    )

    if not is_configured():
        raise HTTPException(
            status_code=400,
            detail="GitHub not configured. Set your GitHub token via Settings or .env"
        )

    remote_url = GitManager.get_remote_url(ACTIVE_TWIN.repo_path)
    if not remote_url:
        raise HTTPException(status_code=400, detail="No git remote 'origin' found.")

    info = extract_owner_repo(remote_url)
    if not info:
        raise HTTPException(status_code=400, detail=f"Could not parse GitHub owner/repo from: {remote_url}")

    # Inspect local branches
    import git
    repo = git.Repo(ACTIVE_TWIN.repo_path)
    local_branches = [b.name for b in repo.branches]
    current_active_branch = str(repo.active_branch.name) if not repo.head.is_detached else "main"

    head = req.head_branch.strip() if req.head_branch else current_active_branch

    # If requested branch does not exist locally, create it from current HEAD
    if head not in local_branches:
        GitManager.create_branch(ACTIVE_TWIN.repo_path, head)

    # Detect authenticated user for cross-repo / fork PRs
    user_info = get_authenticated_user()
    auth_username = user_info.get("username") if user_info.get("status") == "success" else None

    # Check if this is a fork — if so, detect the parent repo for cross-fork PR
    repo_info = get_repo_info(info["owner"], info["repo"])
    target_owner = info["owner"]
    target_repo = info["repo"]
    head_repo_owner = ""

    if repo_info.get("is_fork") and repo_info.get("parent"):
        parent_parts = repo_info["parent"].split("/")
        if len(parent_parts) == 2:
            target_owner = parent_parts[0]
            target_repo = parent_parts[1]
            head_repo_owner = info["owner"]
    elif auth_username and auth_username.lower() != target_owner.lower():
        # Authenticated user is contributing from their own fork/namespace
        head_repo_owner = auth_username

    # Prevent invalid PR where head and base are identical on the same repo
    if not head_repo_owner and head == req.base_branch:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create Pull Request from '{head}' into '{req.base_branch}' on the same repository. Use a feature branch or fork."
        )

    # Ensure branch is pushed to remote before creating PR
    push_res = GitManager.push_to_remote(ACTIVE_TWIN.repo_path, branch=head)
    if push_res.get("status") == "error":
        raise HTTPException(
            status_code=400,
            detail=f"Could not push branch '{head}' to remote: {push_res.get('message')}. Ensure your GitHub token has 'repo' & 'workflow' permissions."
        )


    # Generate rich PR body if not custom
    body = req.body
    if not body or body == "Auto-generated code changes from the 7-Agent SDLC pipeline.":
        body = generate_pr_body(
            task_prompt=req.title,
            generated_files=[],
        )

    result = gh_create_pr(
        owner=target_owner,
        repo=target_repo,
        title=req.title,
        body=body,
        head_branch=head,
        base_branch=req.base_branch,
        head_repo_owner=head_repo_owner,
    )

    if result.get("status") == "error":
        err_msg = result.get("error", "PR creation failed")
        if "head" in err_msg.lower() and "invalid" in err_msg.lower():
            err_msg = (
                f"GitHub could not find new commits between branch '{head}' and target repository '{target_owner}/{target_repo}'. "
                "Make sure you have modified code files and committed them before opening a Pull Request."
            )
        raise HTTPException(status_code=400, detail=err_msg)

    return result


@router.get("/git/status")
def get_git_status():
    """Get comprehensive git status: branch, diff info, remote, GitHub config, repo access."""
    if not ACTIVE_TWIN:
        return {"status": "inactive", "message": "No repository scanned yet."}

    git_info = GitManager.get_repo_git_info(ACTIVE_TWIN.repo_path)
    diff_info = GitManager.get_diff(ACTIVE_TWIN.repo_path)

    from app.utils.github_api import is_configured as gh_configured, extract_owner_repo, get_repo_info, get_authenticated_user

    result = {
        "status": "active",
        "git": git_info,
        "diff": {
            "has_changes": diff_info.get("has_changes", False),
            "staged_files": diff_info.get("staged_files", 0),
            "untracked_files": diff_info.get("untracked_files", 0),
        },
        "github_configured": gh_configured(),
        "repo_access": None,
        "github_user": None,
    }

    # If GitHub is configured, get access info
    if gh_configured() and git_info.get("remote_url"):
        info = extract_owner_repo(git_info["remote_url"])
        if info:
            repo_info = get_repo_info(info["owner"], info["repo"])
            result["repo_access"] = {
                "can_push": repo_info.get("can_push", False),
                "is_fork": repo_info.get("is_fork", False),
                "parent": repo_info.get("parent"),
                "default_branch": repo_info.get("default_branch", "main"),
            }
        user_info = get_authenticated_user()
        if user_info.get("status") == "success":
            result["github_user"] = user_info.get("username")

    return result


# ──── GitHub Token Setup (from UI) ────

class GitHubTokenRequest(BaseModel):
    token: str


@router.post("/github/setup")
def setup_github_token(req: GitHubTokenRequest):
    """
    Set GitHub token at runtime from the frontend settings panel.
    Persists token to backend/.env and memory.
    """
    from app.utils.github_api import set_token, is_configured, get_authenticated_user

    token_str = req.token.strip()
    if not token_str:
        set_token("")
        # Remove or clear from .env
        _update_env_github_token("")
        return {"status": "success", "configured": False, "message": "GitHub token cleared."}

    set_token(token_str)

    # Verify the token works
    user = get_authenticated_user()
    if user.get("status") == "success":
        # Persist to .env
        _update_env_github_token(token_str)
        return {
            "status": "success",
            "configured": True,
            "username": user.get("username"),
            "message": f"GitHub connected as @{user.get('username')}",
        }
    else:
        set_token("")  # Clear invalid token
        return {
            "status": "error",
            "configured": False,
            "message": f"Invalid token: {user.get('error', 'Authentication failed')}",
        }


def _update_env_github_token(token: str):
    """Safely persist GITHUB_TOKEN in backend/.env."""
    try:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            found = False
            for line in lines:
                if line.strip().startswith("GITHUB_TOKEN=") or line.strip().startswith("# GITHUB_TOKEN="):
                    if token:
                        new_lines.append(f"GITHUB_TOKEN={token}\n")
                    else:
                        new_lines.append("# GITHUB_TOKEN=\n")
                    found = True
                else:
                    new_lines.append(line)
            if not found and token:
                new_lines.append(f"\nGITHUB_TOKEN={token}\n")
            with open(env_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            os.environ["GITHUB_TOKEN"] = token
    except Exception as e:
        print(f"[ENV] Could not write GITHUB_TOKEN to .env: {e}")



# ──── Fork Repository ────

class ForkRequest(BaseModel):
    owner: str
    repo: str


@router.post("/github/fork")
def fork_repository(req: ForkRequest):
    """
    Fork a GitHub repository to the authenticated user's account.

    Use case: Fresher doesn't have write access to company repo,
    so they fork it first, then push changes to their fork,
    then open a cross-fork PR to the original repo.
    """
    from app.utils.github_api import is_configured, fork_repo

    if not is_configured():
        raise HTTPException(status_code=400, detail="Set your GitHub token first via Settings.")

    result = fork_repo(req.owner, req.repo)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("error", "Fork failed"))

    # If fork succeeded, update the local remote to point to the fork
    if ACTIVE_TWIN and result.get("fork_clone_url"):
        try:
            import git
            repo = git.Repo(ACTIVE_TWIN.repo_path)
            # Add fork as 'origin' (rename old origin to 'upstream')
            if "origin" in [r.name for r in repo.remotes]:
                # Keep original as 'upstream' for PR targeting
                if "upstream" not in [r.name for r in repo.remotes]:
                    repo.remote("origin").rename("upstream")
                    repo.create_remote("origin", result["fork_clone_url"])
                else:
                    repo.remote("origin").set_url(result["fork_clone_url"])
            else:
                repo.create_remote("origin", result["fork_clone_url"])
        except Exception as e:
            result["remote_update"] = f"Could not update remote: {str(e)}"

    return result


@router.get("/github/repo-info")
def get_github_repo_info(owner: str, repo: str):
    """Get GitHub repository info including access permissions."""
    from app.utils.github_api import is_configured, get_repo_info

    if not is_configured():
        raise HTTPException(status_code=400, detail="GitHub not configured.")

    return get_repo_info(owner, repo)


class SetRemoteRequest(BaseModel):
    remote_url: str
    remote_name: str = "origin"


@router.post("/git/set-remote")
def set_git_remote(req: SetRemoteRequest):
    """Update or add a git remote URL (e.g. pointing to a personal fork)."""
    if not ACTIVE_TWIN:
        raise HTTPException(status_code=404, detail="No repository scanned yet.")
    try:
        import git
        repo = git.Repo(ACTIVE_TWIN.repo_path)
        if req.remote_name in [r.name for r in repo.remotes]:
            repo.remote(req.remote_name).set_url(req.remote_url)
        else:
            repo.create_remote(req.remote_name, req.remote_url)
        return {
            "status": "success",
            "remote_name": req.remote_name,
            "remote_url": req.remote_url,
            "message": f"Remote '{req.remote_name}' set to {req.remote_url}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update remote: {str(e)}")


