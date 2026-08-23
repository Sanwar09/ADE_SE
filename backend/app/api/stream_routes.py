"""
Server-Sent Events (SSE) streaming endpoint for real-time pipeline progress.
Each agent emits events as it starts/finishes, streamed live to the frontend.
"""

import json
import time
import asyncio
import queue
import threading
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.orchestrator import build_orchestrator
from app.twin.scanner import RepositoryScanner
import app.api.twin_routes as twin_routes

router = APIRouter(prefix="/api/agents", tags=["Pipeline Streaming"])


class StreamRunRequest(BaseModel):
    task_prompt: str
    repo_path: str = ""


def _run_pipeline_with_events(task_prompt: str, repo_path: str, event_queue: queue.Queue):
    """
    Run the 7-agent pipeline in a background thread, pushing SSE events
    to the event_queue as each agent starts/finishes.
    """
    try:
        file_store = twin_routes.ACTIVE_FILE_STORE
        twin = twin_routes.ACTIVE_TWIN

        if not file_store or not twin:
            event_queue.put({"event": "error", "data": {"message": "No repository scanned."}})
            event_queue.put(None)  # Sentinel to close stream
            return

        actual_repo_path = repo_path or twin.repo_path
        orchestrator = build_orchestrator()

        initial_state = {
            "task_prompt": task_prompt,
            "repo_path": actual_repo_path,
            "current_agent": "Initializing",
            "trajectory_logs": [],
            "file_store": file_store,
            "twin": twin,
            "user_story": None,
            "architecture_plan": None,
            "security_report": None,
            "generated_code": None,
            "original_code": None,
            "test_results": None,
            "test_attempts": 0,
            "review_verdict": None,
            "devops_summary": None,
            "status": "IN_PROGRESS",
        }

        event_queue.put({
            "event": "pipeline_start",
            "data": {"message": "Pipeline started", "task": task_prompt}
        })

        # Hook into the orchestrator — we'll track agent changes
        # by polling the state after invocation
        prev_agent = ""
        prev_log_count = 0

        # We use invoke which runs all nodes synchronously
        # To get per-agent events, we use stream mode
        try:
            for step_output in orchestrator.stream(initial_state):
                # step_output is a dict with the node name as key
                for node_name, node_state in step_output.items():
                    agent_name = node_state.get("current_agent", node_name)
                    logs = node_state.get("trajectory_logs", [])

                    # Emit agent start
                    event_queue.put({
                        "event": "agent_start",
                        "data": {"agent": agent_name, "node": node_name}
                    })

                    # Emit any new log entries
                    for log in logs[prev_log_count:]:
                        event_queue.put({
                            "event": "agent_log",
                            "data": {
                                "agent": log.get("agent", agent_name),
                                "action": log.get("action", ""),
                                "output": (log.get("output", "") or "")[:2000],
                            }
                        })

                    prev_log_count = len(logs)

                    # Emit agent complete
                    event_queue.put({
                        "event": "agent_complete",
                        "data": {"agent": agent_name, "node": node_name}
                    })

                    # Keep final state
                    final_state = node_state

        except Exception as stream_err:
            # Fallback: run without streaming
            event_queue.put({
                "event": "info",
                "data": {"message": f"Streaming unavailable, running synchronously: {str(stream_err)[:100]}"}
            })
            final_state = orchestrator.invoke(initial_state)

            for log in final_state.get("trajectory_logs", []):
                event_queue.put({
                    "event": "agent_log",
                    "data": {
                        "agent": log.get("agent", ""),
                        "action": log.get("action", ""),
                        "output": (log.get("output", "") or "")[:2000],
                    }
                })

        # Build safe result (remove non-serializable objects)
        safe_state = dict(final_state)
        safe_state.pop("file_store", None)
        safe_state.pop("twin", None)

        event_queue.put({
            "event": "pipeline_complete",
            "data": {
                "status": "success",
                "task_prompt": task_prompt,
                "trajectory_logs": safe_state.get("trajectory_logs", []),
                "generated_code": safe_state.get("generated_code", {}),
                "original_code": safe_state.get("original_code", {}),
                "test_results": safe_state.get("test_results"),
                "review_verdict": safe_state.get("review_verdict"),
                "devops_summary": safe_state.get("devops_summary"),
                "architecture_plan": safe_state.get("architecture_plan"),
                "pipeline_status": safe_state.get("status", "completed"),
            }
        })

    except Exception as e:
        event_queue.put({
            "event": "error",
            "data": {"message": f"Pipeline failed: {str(e)}"}
        })
    finally:
        event_queue.put(None)  # Sentinel — end of stream


@router.post("/run-stream")
async def run_pipeline_stream(req: StreamRunRequest):
    """
    SSE streaming endpoint: runs the 7-Agent SDLC pipeline and streams
    real-time progress events to the frontend via Server-Sent Events.
    """
    if not twin_routes.ACTIVE_FILE_STORE or not twin_routes.ACTIVE_TWIN:
        raise HTTPException(
            status_code=400,
            detail="No repository scanned. Scan a repo first via /api/twin/scan"
        )

    repo_path = req.repo_path or twin_routes.ACTIVE_TWIN.repo_path
    event_queue = queue.Queue()

    # Start pipeline in background thread
    thread = threading.Thread(
        target=_run_pipeline_with_events,
        args=(req.task_prompt, repo_path, event_queue),
        daemon=True,
    )
    thread.start()

    async def event_generator():
        while True:
            try:
                # Non-blocking check with small timeout
                event = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: event_queue.get(timeout=0.5)
                )
                if event is None:
                    # Sentinel — pipeline finished
                    break
                yield f"data: {json.dumps(event)}\n\n"
            except queue.Empty:
                # Send keepalive to prevent timeout
                yield f": keepalive\n\n"
            except Exception:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
