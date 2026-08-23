import os
import re
import time
from typing import Dict, Any, Optional
import git


class GitManager:
    """
    Handles Git operations: cloning from GitHub, committing changes,
    push to remote, branch management, diff generation, and local workspace mgmt.
    All push/PR operations are USER-INITIATED — never automatic.
    """

    WORKSPACE_DIR = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))),
        "workspace"
    )

    @staticmethod
    def clone(github_url: str) -> str:
        """Clone a GitHub repository. Returns local absolute path."""
        if not os.path.exists(GitManager.WORKSPACE_DIR):
            os.makedirs(GitManager.WORKSPACE_DIR, exist_ok=True)

        repo_name = github_url.rstrip("/").split("/")[-1]
        if repo_name.endswith(".git"):
            repo_name = repo_name[:-4]

        local_path = os.path.join(GitManager.WORKSPACE_DIR, repo_name)
        if not os.path.exists(local_path):
            git.Repo.clone_from(github_url, local_path)
        return os.path.abspath(local_path)

    @staticmethod
    def is_github_url(input_str: str) -> bool:
        """Check if input is a valid GitHub URL."""
        pattern = r"^(https?://)?(www\.)?github\.com/[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/?.*$"
        return bool(re.match(pattern, input_str.strip()))

    @staticmethod
    def commit_changes(repo_path: str, commit_message: str = "Apply autonomous SDLC changes via ADT-SE") -> Dict[str, Any]:
        """Commit all modified and untracked files to the repository's git history."""
        try:
            try:
                repo = git.Repo(repo_path)
            except git.exc.InvalidGitRepositoryError:
                # Initialize git repo if not present
                repo = git.Repo.init(repo_path)

            repo.git.add(all=True)

            # Check if there are changes to commit
            if repo.is_dirty(untracked_files=True):
                commit = repo.index.commit(commit_message)
                return {
                    "status": "success",
                    "committed": True,
                    "commit_hash": commit.hexsha[:8],
                    "message": commit_message,
                    "branch": str(repo.active_branch) if not repo.head.is_detached else "detached"
                }
            else:
                return {
                    "status": "success",
                    "committed": False,
                    "message": "Working directory clean — no changes to commit."
                }
        except Exception as e:
            return {
                "status": "error",
                "committed": False,
                "message": f"Git commit failed: {str(e)}"
            }

    @staticmethod
    def create_branch(repo_path: str, branch_name: str = "") -> Dict[str, Any]:
        """
        Create and checkout a new feature branch.
        If no branch_name provided, auto-generates one.
        """
        try:
            repo = git.Repo(repo_path)
            if not branch_name:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                branch_name = f"feature/adt-se-{timestamp}"

            # Create and checkout
            current = repo.active_branch.name if not repo.head.is_detached else "HEAD"
            new_branch = repo.create_head(branch_name)
            new_branch.checkout()

            return {
                "status": "success",
                "branch": branch_name,
                "previous_branch": current,
                "message": f"Created and switched to branch: {branch_name}"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Branch creation failed: {str(e)}"
            }

    @staticmethod
    def get_diff(repo_path: str) -> Dict[str, Any]:
        """Get the current diff (staged + unstaged changes)."""
        try:
            repo = git.Repo(repo_path)

            # Unstaged changes
            unstaged_diff = repo.git.diff()
            # Staged changes
            staged_diff = repo.git.diff("--cached")
            # Untracked files
            untracked = repo.untracked_files

            combined = ""
            if staged_diff:
                combined += f"=== STAGED CHANGES ===\n{staged_diff}\n\n"
            if unstaged_diff:
                combined += f"=== UNSTAGED CHANGES ===\n{unstaged_diff}\n\n"
            if untracked:
                combined += f"=== UNTRACKED FILES ===\n" + "\n".join(untracked)

            return {
                "status": "success",
                "diff": combined or "No changes detected.",
                "has_changes": bool(staged_diff or unstaged_diff or untracked),
                "staged_files": len(staged_diff.split("diff --git")) - 1 if staged_diff else 0,
                "untracked_files": len(untracked),
            }
        except Exception as e:
            return {"status": "error", "diff": "", "message": str(e)}

    @staticmethod
    def push_to_remote(repo_path: str, branch: str = "", remote: str = "origin") -> Dict[str, Any]:
        """
        Push the current branch to the remote.
        USER-INITIATED ONLY — never called automatically.
        Requires git credentials configured (PAT, SSH key, or credential helper).
        """
        try:
            repo = git.Repo(repo_path)
            if not branch:
                branch = str(repo.active_branch) if not repo.head.is_detached else "main"

            # Check if remote exists
            if remote not in [r.name for r in repo.remotes]:
                return {
                    "status": "error",
                    "message": f"Remote '{remote}' not found. This repo has remotes: {[r.name for r in repo.remotes]}"
                }

            # Set upstream and push
            from app.utils.github_api import _get_token
            github_token = _get_token()
            remote_obj = repo.remote(remote)

            # If PAT is available, inject it into the URL for auth
            if github_token:
                remote_url = remote_obj.url
                if "github.com" in remote_url:
                    # Clean existing auth from URL if present
                    clean_url = re.sub(r"https?://[^@]+@github\.com", "https://github.com", remote_url)
                    auth_url = clean_url.replace(
                        "https://github.com",
                        f"https://x-access-token:{github_token}@github.com"
                    )
                    remote_obj.set_url(auth_url)
                    try:
                        push_info = remote_obj.push(branch, set_upstream=True)
                        for info in push_info:
                            if info.flags & (info.ERROR | info.REJECTED):
                                raise Exception(info.summary or f"Push rejected: {info.flags}")
                    finally:
                        # Restore clean URL (don't persist token in local config)
                        remote_obj.set_url(clean_url)
                else:
                    push_info = remote_obj.push(branch, set_upstream=True)
            else:
                push_info = remote_obj.push(branch, set_upstream=True)

            return {
                "status": "success",
                "branch": branch,
                "remote": remote,
                "message": f"Successfully pushed '{branch}' to {remote}"
            }
        except Exception as e:
            error_msg = str(e)
            if "authentication" in error_msg.lower() or "403" in error_msg or "401" in error_msg:
                return {
                    "status": "error",
                    "message": "Authentication failed. Set GITHUB_TOKEN in .env or configure git credentials."
                }
            return {"status": "error", "message": f"Push failed: {error_msg}"}

    @staticmethod
    def get_remote_url(repo_path: str) -> Optional[str]:
        """Get the remote origin URL of a repo."""
        try:
            repo = git.Repo(repo_path)
            if "origin" in [r.name for r in repo.remotes]:
                return repo.remote("origin").url
        except Exception:
            pass
        return None

    @staticmethod
    def get_repo_git_info(repo_path: str) -> Optional[Dict[str, Any]]:
        """Get git metadata (branch, latest commit) for a repository path."""
        try:
            repo = git.Repo(repo_path)
            head_commit = repo.head.commit
            remote_url = None
            if "origin" in [r.name for r in repo.remotes]:
                remote_url = repo.remote("origin").url

            return {
                "is_git_repo": True,
                "branch": str(repo.active_branch) if not repo.head.is_detached else "detached",
                "commit_hash": head_commit.hexsha[:8],
                "commit_message": head_commit.message.strip(),
                "is_dirty": repo.is_dirty(untracked_files=True),
                "remote_url": remote_url,
            }
        except Exception:
            return {
                "is_git_repo": False,
                "branch": "none",
                "commit_hash": "none",
                "commit_message": "Not a git repo",
                "is_dirty": False,
                "remote_url": None,
            }
