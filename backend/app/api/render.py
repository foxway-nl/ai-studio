"""Render API router – video rendering taken en status."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_engine, get_session
from app.models.models import Episode, RenderJob, Scene
from app.schemas.schemas import RenderJobResponse
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Render"])


class RenderRequestPayload(BaseModel):
    episode_id: str
    resolution: Optional[str] = "1920x1080"
    fps: Optional[int] = 30


def _fixed_bumper(name: str) -> Optional[str]:
    """Zoek een vaste intro/outro bumper in de persistente assets-map."""
    candidates = [
        settings.assets_dir / "fixed" / name,
        settings.assets_dir / name,
        Path("/app/assets/fixed") / name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return None


@router.post("/api/render")
@router.post("/api/episodes/{episode_id}/render/start")
async def start_render(
    payload: Optional[RenderRequestPayload] = None,
    episode_id: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Start de video-rendering van een aflevering via FFmpeg."""
    target_ep_id = episode_id or (payload.episode_id if payload else None)
    if not target_ep_id:
        raise HTTPException(status_code=400, detail="episode_id is verplicht.")

    episode = session.get(Episode, target_ep_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    resolution = (payload.resolution if payload else None) or "1920x1080"
    fps = (payload.fps if payload else None) or 30
    bg_music_path = episode.bg_music_path or None

    # Vaste intro/outro bumpers (optioneel; alleen als de bestanden bestaan).
    intro_path = _fixed_bumper("intro_bumper.mp4")
    outro_path = _fixed_bumper("outro_bumper.mp4")

    scenes = session.exec(
        select(Scene).where(Scene.episode_id == target_ep_id).order_by(Scene.scene_number.asc())
    ).all()
    if not scenes:
        raise HTTPException(status_code=400, detail="De aflevering bevat nog geen scènes.")

    task_id = f"render_{target_ep_id}_{uuid.uuid4().hex[:6]}"

    # Maak database record aan
    render_job = RenderJob(
        id=task_id,
        episode_id=target_ep_id,
        status="queued",
        progress=0.0,
        current_step="In de wachtrij voor rendering...",
        resolution=resolution,
        fps=fps,
        started_at=datetime.now(timezone.utc),
    )
    session.add(render_job)
    session.commit()

    # Verzamel scène data
    scenes_data = [
        {
            "id": s.id,
            "scene_number": s.scene_number,
            "title": s.title,
            "narration_text": s.narration_text,
            "duration_seconds": s.duration_seconds,
            "animation_type": s.animation_type,
            "transition_type": s.transition_type,
            "chapter_type": s.chapter_type,
            "background_image_path": s.background_image_path,
            "composite_image_path": s.composite_image_path,
            "audio_path": s.audio_path,
            "sfx_track": s.sfx_track,
            "pause_after_sec": s.pause_after_sec,
            "word_timestamps": s.word_timestamps,
        }
        for s in scenes
    ]

    async def _run_render():
        from app.services.ffmpeg_service import ffmpeg_service

        output_filename = f"episode_{target_ep_id}_{uuid.uuid4().hex[:6]}.mp4"
        output_path = str(settings.renders_dir / output_filename)

        def _on_progress(pct: float, step: str):
            task_manager.update_progress(task_id, pct, step)
            engine = get_engine()
            with Session(engine) as db:
                rj = db.get(RenderJob, task_id)
                if rj:
                    rj.progress = pct
                    rj.current_step = step
                    rj.status = "rendering" if pct < 1.0 else "complete"
                    db.add(rj)
                    db.commit()

        task_manager.update_progress(task_id, 0.05, "Scène clips voorbereiden...")
        try:
            await ffmpeg_service.render_episode(
                scenes_data=scenes_data,
                output_path=output_path,
                resolution=resolution,
                fps=fps,
                bg_music_path=bg_music_path,
                intro_path=intro_path,
                outro_path=outro_path,
                progress_callback=_on_progress,
            )

            engine = get_engine()
            with Session(engine) as db:
                rj = db.get(RenderJob, task_id)
                if rj:
                    rj.status = "complete"
                    rj.progress = 1.0
                    rj.current_step = "Video render succesvol voltooid!"
                    # Sla relatieve media URL op
                    rj.output_path = f"/media/renders/{output_filename}"
                    rj.completed_at = datetime.now(timezone.utc)
                    db.add(rj)

                ep = db.get(Episode, target_ep_id)
                if ep:
                    ep.status = "rendered"
                    ep.updated_at = datetime.now(timezone.utc)
                    db.add(ep)
                db.commit()

            return {"output_path": f"/media/renders/{output_filename}"}

        except Exception as e:
            logger.exception("Fout tijdens render taak: %s", e)
            engine = get_engine()
            with Session(engine) as db:
                rj = db.get(RenderJob, task_id)
                if rj:
                    rj.status = "error"
                    rj.error_message = str(e)
                    db.add(rj)
                    db.commit()
            raise e

    task_manager.start_task(task_id, _run_render())
    return {"task_id": task_id, "render_job_id": task_id}


@router.get("/api/episodes/{episode_id}/render", response_model=List[RenderJobResponse])
async def list_renders_for_episode(episode_id: str, session: Session = Depends(get_session)):
    """Lijst alle render jobs voor een aflevering op."""
    jobs = session.exec(
        select(RenderJob).where(RenderJob.episode_id == episode_id).order_by(RenderJob.created_at.desc())
    ).all()
    return jobs

