import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.api.twin_routes import router as twin_router
from app.api.agent_routes import router as agent_router
from app.api.explainer_routes import router as explainer_router
from app.api.stream_routes import router as stream_router

load_dotenv()

app = FastAPI(
    title="ADT-SE Backend API",
    description="Agentic Digital Twin for Software Engineering - 7-Agent Autonomous SDLC Platform",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(twin_router)
app.include_router(agent_router)
app.include_router(explainer_router)
app.include_router(stream_router)


@app.get("/health")
async def health_check():
    """System health with configuration status."""
    from app.utils.llm import get_model_name, API_KEYS
    from app.utils.github_api import is_configured as gh_configured

    api_key_configured = len(API_KEYS) > 0
    model = get_model_name()

    return {
        "status": "ok",
        "version": "2.0.0",
        "model": model,
        "api_keys_loaded": len(API_KEYS),
        "api_key_configured": api_key_configured,
        "github_configured": gh_configured(),
    }


@app.on_event("startup")
async def startup_validation():
    """Validate critical configuration on startup."""
    from app.utils.llm import API_KEYS, get_model_name

    model = get_model_name()
    print(f"\n{'='*60}")
    print(f"  ADT-SE Backend v2.0.0")
    print(f"  Model: {model}")
    print(f"  API Keys loaded: {len(API_KEYS)}")

    if not API_KEYS:
        print(f"  [WARNING] No GEMINI_API_KEY configured in .env")
        print(f"     The system will run in DEMO MODE.")
    else:
        print(f"  [OK] API key(s) configured")

    github_token = os.getenv("GITHUB_TOKEN", "")
    if github_token and github_token != "your_github_token_here":
        print(f"  [OK] GitHub token configured (push/PR enabled)")
    else:
        print(f"  [INFO] GitHub token not set (push/PR disabled -- local-only mode)")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
