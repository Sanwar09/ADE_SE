import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict
from app.agents.orchestrator import build_orchestrator
from app.twin.scanner import RepositoryScanner
import app.api.twin_routes as twin_routes

router = APIRouter(prefix="/api/agents", tags=["Multi-Agent Pipeline"])


class RunAgentRequest(BaseModel):
    task_prompt: str
    repo_path: str = ""


class MergeRequest(BaseModel):
    repo_path: str = ""
    files_to_write: Dict[str, str] = {}


@router.post("/run")
def run_agent_workflow(req: RunAgentRequest):
    """
    Execute the complete 7-Agent SDLC pipeline.
    Requires a scanned repository (call /api/twin/scan first).
    """
    if not twin_routes.ACTIVE_FILE_STORE or not twin_routes.ACTIVE_TWIN:
        raise HTTPException(
            status_code=400,
            detail="No repository scanned. Please scan a repo first via /api/twin/scan or /api/twin/clone."
        )

    repo_path = req.repo_path or twin_routes.ACTIVE_TWIN.repo_path

    # Build a fresh orchestrator for each run
    orchestrator = build_orchestrator()

    initial_state = {
        "task_prompt": req.task_prompt,
        "repo_path": repo_path,
        "current_agent": "Initializing",
        "trajectory_logs": [],
        "file_store": twin_routes.ACTIVE_FILE_STORE,
        "twin": twin_routes.ACTIVE_TWIN,
        "user_story": None,
        "architecture_plan": None,
        "security_report": None,
        "generated_code": None,
        "original_code": None,
        "test_results": None,
        "test_attempts": 0,
        "review_verdict": None,
        "devops_summary": None,
        "status": "IN_PROGRESS"
    }

    try:
        final_state = orchestrator.invoke(initial_state)

        # Remove non-serializable objects before returning
        safe_state = dict(final_state)
        safe_state.pop("file_store", None)
        safe_state.pop("twin", None)

        return {
            "status": "success",
            "task_prompt": req.task_prompt,
            "trajectory_logs": safe_state.get("trajectory_logs", []),
            "generated_code": safe_state.get("generated_code", {}),
            "original_code": safe_state.get("original_code", {}),
            "test_results": safe_state.get("test_results"),
            "review_verdict": safe_state.get("review_verdict"),
            "devops_summary": safe_state.get("devops_summary"),
            "architecture_plan": safe_state.get("architecture_plan"),
            "pipeline_status": safe_state.get("status", "completed")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution failed: {str(e)}")


@router.post("/merge")
def merge_to_disk(req: MergeRequest):
    """
    PHYSICALLY write generated code files to disk, then re-index the Digital Twin.
    """
    if not twin_routes.ACTIVE_TWIN:
        raise HTTPException(status_code=400, detail="No active repository.")

    repo_path = req.repo_path or twin_routes.ACTIVE_TWIN.repo_path
    target_dir = os.path.abspath(repo_path)

    if not os.path.exists(target_dir):
        raise HTTPException(status_code=400, detail=f"Directory does not exist: {target_dir}")

    if not req.files_to_write:
        raise HTTPException(status_code=400, detail="No files provided to merge.")

    written_files = []
    try:
        for rel_path, content in req.files_to_write.items():
            full_path = os.path.join(target_dir, rel_path)
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            written_files.append(rel_path)

        # Re-index the Digital Twin after merging
        scanner = RepositoryScanner(target_dir)
        twin_routes.ACTIVE_TWIN, twin_routes.ACTIVE_FILE_STORE = scanner.scan()

        meta = dict(twin_routes.ACTIVE_TWIN.metadata)
        meta["languages"] = list(meta.get("languages", set()))

        return {
            "status": "success",
            "message": f"Merged {len(written_files)} files to disk",
            "written_files": written_files,
            "updated_metadata": meta
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Merge failed: {str(e)}")


class DeployRequest(BaseModel):
    repo_path: str = ""
    files_to_write: Dict[str, str] = {}
    commit_message: str = "Autonomous SDLC update via ADT-SE"
    create_branch: bool = True
    branch_name: str = ""
    push_to_github: bool = False  # USER CHOICE — never automatic
    create_pr: bool = False  # USER CHOICE — never automatic
    pr_title: str = "ADT-SE: Autonomous Code Update"
    pr_body: str = ""


@router.post("/deploy")
def one_click_deploy(req: DeployRequest):
    """
    One-Click Deploy: Branch → Merge → Re-index → Commit → (Optional) Push → (Optional) PR
    Supports both direct repo PR and cross-fork PR workflows for team collaboration.
    GitHub operations ONLY happen if the user explicitly requests them.
    """
    if not twin_routes.ACTIVE_TWIN:
        candidate = req.repo_path or "c:/Final Year/workspace/Doclarity"
        if candidate and os.path.exists(candidate):
            try:
                scanner = RepositoryScanner(candidate)
                twin_routes.ACTIVE_TWIN, twin_routes.ACTIVE_FILE_STORE = scanner.scan()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Could not load repository: {str(e)}")
        else:
            raise HTTPException(status_code=400, detail="No active repository. Please scan repository first.")

    from app.twin.git_manager import GitManager
    from app.utils.github_api import (
        is_configured, extract_owner_repo, create_pull_request as gh_create_pr,
        generate_pr_body, get_repo_info
    )

    repo_path = req.repo_path or twin_routes.ACTIVE_TWIN.repo_path
    target_dir = os.path.abspath(repo_path)
    results = {"steps": []}

    # Step 0: Create Feature Branch if requested
    if req.create_branch:
        branch_res = GitManager.create_branch(target_dir, req.branch_name)
        results["steps"].append({
            "step": "branch",
            "status": branch_res.get("status", "error"),
            "branch": branch_res.get("branch"),
            "message": branch_res.get("message", "")
        })

    # Step 1: Write files to disk
    if req.files_to_write:
        try:
            written_files = []
            for rel_path, content in req.files_to_write.items():
                full_path = os.path.join(target_dir, rel_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(content)
                written_files.append(rel_path)
            results["steps"].append({
                "step": "merge",
                "status": "success",
                "message": f"Merged {len(written_files)} files to disk"
            })
        except Exception as e:
            results["steps"].append({"step": "merge", "status": "error", "message": str(e)})
            return results

    # Step 2: Re-index Digital Twin
    try:
        scanner = RepositoryScanner(target_dir)
        twin_routes.ACTIVE_TWIN, twin_routes.ACTIVE_FILE_STORE = scanner.scan()
        results["steps"].append({"step": "re-index", "status": "success"})
    except Exception as e:
        results["steps"].append({"step": "re-index", "status": "error", "message": str(e)})

    # Step 3: Git Commit
    commit_res = GitManager.commit_changes(target_dir, req.commit_message)
    results["steps"].append({
        "step": "commit",
        "status": commit_res.get("status", "error"),
        "commit_hash": commit_res.get("commit_hash"),
        "message": commit_res.get("message", "")
    })

    # Step 4: Push to GitHub (ONLY if user requested)
    if req.push_to_github:
        git_info = GitManager.get_repo_git_info(target_dir)
        active_branch = git_info.get("branch", "main")
        push_res = GitManager.push_to_remote(target_dir, branch=active_branch)
        results["steps"].append({
            "step": "push",
            "status": push_res.get("status", "error"),
            "branch": active_branch,
            "message": push_res.get("message", "")
        })

        # Step 5: Create PR (ONLY if user requested AND push succeeded)
        if req.create_pr and push_res.get("status") == "success":
            if is_configured():
                remote_url = GitManager.get_remote_url(target_dir)
                info = extract_owner_repo(remote_url) if remote_url else None
                if info:
                    repo_info = get_repo_info(info["owner"], info["repo"])
                    target_owner = info["owner"]
                    target_repo = info["repo"]
                    head_repo_owner = ""

                    from app.utils.github_api import get_authenticated_user
                    user_info = get_authenticated_user()
                    auth_username = user_info.get("username") if user_info.get("status") == "success" else None

                    # Detect if fork for cross-fork PR
                    if repo_info.get("is_fork") and repo_info.get("parent"):
                        parent_parts = repo_info["parent"].split("/")
                        if len(parent_parts) == 2:
                            target_owner = parent_parts[0]
                            target_repo = parent_parts[1]
                            head_repo_owner = info["owner"]
                    elif auth_username and auth_username.lower() != target_owner.lower():
                        head_repo_owner = auth_username

                    pr_body = req.pr_body or generate_pr_body(
                        task_prompt=req.pr_title,
                        generated_files=list(req.files_to_write.keys()) if req.files_to_write else [],
                    )

                    pr_res = gh_create_pr(
                        owner=target_owner,
                        repo=target_repo,
                        title=req.pr_title,
                        body=pr_body,
                        head_branch=active_branch,
                        head_repo_owner=head_repo_owner,
                    )
                    results["steps"].append({
                        "step": "pr",
                        "status": pr_res.get("status", "error"),
                        "pr_url": pr_res.get("pr_url"),
                        "pr_number": pr_res.get("pr_number"),
                        "target_repo": f"{target_owner}/{target_repo}",
                        "message": pr_res.get("message") or pr_res.get("error", "PR processed")
                    })
                else:
                    results["steps"].append({
                        "step": "pr", "status": "skipped",
                        "message": "Could not detect GitHub remote URL"
                    })
            else:
                results["steps"].append({
                    "step": "pr", "status": "skipped",
                    "message": "GitHub token not configured (set via Settings or .env)"
                })

    results["status"] = "success"
    return results


@router.post("/generate-cicd")
def generate_cicd():
    """Generate CI/CD pipeline files (GitHub Actions, Dockerfile, docker-compose)."""
    if not twin_routes.ACTIVE_FILE_STORE:
        raise HTTPException(status_code=400, detail="No repository scanned.")

    from app.utils.ci_cd_generator import CICDGenerator
    files = CICDGenerator.generate_all(twin_routes.ACTIVE_FILE_STORE, project_name="adt-se")
    return {
        "status": "success",
        "files": files,
        "count": len(files),
    }

