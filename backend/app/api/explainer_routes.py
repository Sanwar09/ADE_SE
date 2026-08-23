from fastapi import APIRouter, HTTPException
from app.twin.explainer import RepositoryExplainer
import app.api.twin_routes as twin_routes

router = APIRouter(prefix="/api/explainer", tags=["System Comprehension"])


@router.get("/summary")
def get_repository_summary():
    """
    Returns comprehensive system architecture report:
    - LLM-powered architecture summary
    - Tech stack & domain overview
    - File tree & folder structure
    - API endpoints & Database schema registry
    - How-To-Run guide
    """
    if not twin_routes.ACTIVE_TWIN or not twin_routes.ACTIVE_FILE_STORE:
        raise HTTPException(
            status_code=404,
            detail="No active Digital Twin found. Please scan a repository first."
        )

    explainer = RepositoryExplainer(
        repo_path=twin_routes.ACTIVE_TWIN.repo_path,
        twin=twin_routes.ACTIVE_TWIN,
        file_store=twin_routes.ACTIVE_FILE_STORE
    )
    report = explainer.generate_comprehension_report()

    return {
        "status": "success",
        "report": report
    }
