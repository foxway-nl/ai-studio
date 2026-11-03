"""Server-Sent Events (SSE) router – streaming van real-time taakvoortgang."""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Events"])


@router.get("/api/tasks/{task_id}/progress")
@router.get("/api/events/{task_id}")
@router.get("/api/episodes/{episode_id}/render/{task_id}/events")
@router.get("/api/episodes/{episode_id}/publish/{task_id}/events")
async def stream_task_progress(task_id: str, episode_id: str = ""):
    """Stream real-time voortgang van een achtergrondtaak via Server-Sent Events (SSE)."""
    generator = task_manager.event_generator(task_id)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

