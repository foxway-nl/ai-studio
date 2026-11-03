"""Publish API router – YouTube upload, OAuth2 flow en status."""

import asyncio
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
from app.models.models import Episode, PublishJob, RenderJob
from app.schemas.schemas import PublishJobResponse
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Publish"])


class PublishRequestPayload(BaseModel):
    episode_id: str
    privacy_status: Optional[str] = "private"
    made_for_kids: Optional[bool] = True


class OAuthCallbackPayload(BaseModel):
    code: str
    redirect_uri: Optional[str] = "http://localhost:3000/render/callback"


@router.get("/api/auth/youtube/url")
@router.get("/api/publish/youtube/auth-url")
async def get_youtube_auth_url(redirect_uri: str = "http://localhost:3000/render/callback"):
    """Haal de Google OAuth2 login URL op voor YouTube koppeling."""
    from app.services.youtube_service import youtube_service

    try:
        url = youtube_service.get_auth_url(redirect_uri=redirect_uri)
        return {"auth_url": url}
    except Exception as e:
        logger.warning("Fout bij genereren YouTube auth url: %s", e)
        raise HTTPException(
            status_code=400,
            detail=f"YouTube configuratie ontbreekt of is onjuist: {e}",
        )


@router.post("/api/auth/youtube/callback")
@router.post("/api/publish/youtube/callback")
async def handle_youtube_oauth_callback(payload: OAuthCallbackPayload):
    """Wissel auth-code in voor tokens en sla ze op."""
    from app.services.youtube_service import youtube_service

    try:
        res = youtube_service.exchange_code(
            code=payload.code,
            redirect_uri=payload.redirect_uri or "http://localhost:3000/render/callback",
        )
        return res
    except Exception as e:
        logger.exception("Fout bij uitwisselen OAuth code: %s", e)
        raise HTTPException(status_code=400, detail=f"OAuth fout: {e}")


@router.post("/api/publish/youtube")
@router.post("/api/episodes/{episode_id}/publish/start")
async def publish_to_youtube(
    payload: Optional[PublishRequestPayload] = None,
    episode_id: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Start de publicatie van een gerenderde video naar YouTube."""
    target_ep_id = episode_id or (payload.episode_id if payload else None)
    if not target_ep_id:
        raise HTTPException(status_code=400, detail="episode_id is verplicht.")
    episode = session.get(Episode, target_ep_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    privacy_status = (payload.privacy_status if payload else None) or "private"
    made_for_kids = (
        payload.made_for_kids
        if payload is not None and payload.made_for_kids is not None
        else True
    )

    # ORM-objecten zijn na het sluiten van de request-sessie niet meer veilig
    # te gebruiken; leg alle metadata nu vast voor de achtergrondtaak.
    episode_title = episode.title
    episode_description = episode.description
    episode_seo_title = episode.seo_title
    episode_seo_description = episode.seo_description
    episode_seo_tags = episode.seo_tags or ""

    # Zoek de meest recente succesvol gerenderde video op
    render_job = session.exec(
        select(RenderJob)
        .where(RenderJob.episode_id == target_ep_id)
        .where(RenderJob.status == "complete")
        .order_by(RenderJob.completed_at.desc())  # type: ignore[attr-defined]
    ).first()

    if not render_job or not render_job.output_path:
        raise HTTPException(
            status_code=400,
            detail="Deze aflevering is nog niet gerenderd. Render eerst de video.",
        )

    # Resolveer fysiek pad op schijf
    filename = Path(render_job.output_path).name
    actual_video_path = settings.renders_dir / filename
    if not actual_video_path.exists():
        raise HTTPException(status_code=400, detail=f"Videobestand niet gevonden: {actual_video_path}")

    task_id = f"pub_{target_ep_id}_{uuid.uuid4().hex[:6]}"

    publish_job = PublishJob(
        id=task_id,
        episode_id=target_ep_id,
        status="uploading",
        progress=0.0,
        privacy_status=privacy_status,
        made_for_kids=made_for_kids,
        started_at=datetime.now(timezone.utc),
    )
    session.add(publish_job)
    session.commit()

    async def _run_upload():
        from app.services.youtube_service import youtube_service

        task_manager.update_progress(task_id, 0.05, "YouTube sessie verifiëren...")

        def _on_progress(pct: float, step: str):
            task_manager.update_progress(task_id, pct, step)
            engine = get_engine()
            with Session(engine) as db:
                pj = db.get(PublishJob, task_id)
                if pj:
                    pj.progress = pct
                    db.add(pj)
                    db.commit()

        try:
            loop = asyncio.get_running_loop()
            tags = [t.strip() for t in episode_seo_tags.split(",") if t.strip()]

            res = await loop.run_in_executor(
                None,
                lambda: youtube_service.upload_video(
                    video_path=str(actual_video_path),
                    title=episode_seo_title or episode_title,
                    description=episode_seo_description or episode_description,
                    tags=tags,
                    privacy_status=privacy_status,
                    made_for_kids=made_for_kids,
                    progress_callback=_on_progress,
                ),
            )

            engine = get_engine()
            with Session(engine) as db:
                pj = db.get(PublishJob, task_id)
                if pj:
                    pj.status = "published"
                    pj.progress = 1.0
                    pj.youtube_video_id = res.get("video_id")
                    pj.youtube_url = res.get("url")
                    pj.completed_at = datetime.now(timezone.utc)
                    db.add(pj)

                ep = db.get(Episode, target_ep_id)
                if ep:
                    ep.status = "published"
                    ep.youtube_video_id = res.get("video_id") or ep.youtube_video_id
                    ep.updated_at = datetime.now(timezone.utc)
                    db.add(ep)
                db.commit()

            task_manager.update_progress(task_id, 1.0, f"Video gepubliceerd: {res.get('url')}")
            return res

        except Exception as e:
            logger.exception("Fout tijdens YouTube upload: %s", e)
            engine = get_engine()
            with Session(engine) as db:
                pj = db.get(PublishJob, task_id)
                if pj:
                    pj.status = "error"
                    pj.error_message = str(e)
                    db.add(pj)
                    db.commit()
            raise e

    task_manager.start_task(task_id, _run_upload())
    return {"task_id": task_id, "publish_job_id": task_id}


@router.get("/api/episodes/{episode_id}/publish", response_model=List[PublishJobResponse])
async def list_publish_jobs_for_episode(episode_id: str, session: Session = Depends(get_session)):
    """Lijst alle publicatie jobs voor een aflevering op."""
    jobs = session.exec(
        select(PublishJob).where(PublishJob.episode_id == episode_id).order_by(PublishJob.created_at.desc())
    ).all()
    return jobs

