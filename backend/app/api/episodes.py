"""Episodes CRUD router – beheer van afleveringen binnen een project."""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, func

from app.core.database import get_session
from app.models.models import Episode, Project, PublishJob, RenderJob, Scene
from app.schemas.schemas import (
    EpisodeCreate,
    EpisodeResponse,
    EpisodeUpdate,
    ScriptGenerateRequest,
)
from app.services.guardrails_service import guardrails_service
from app.services.script_service import persist_script_result
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/projects/{project_id}/episodes", tags=["Episodes"])


def _verify_project(project_id: str, session: Session) -> Project:
    """Verifieer dat het project bestaat."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")
    return project


from app.services.image_service import to_media_url


def _episode_to_response(episode: Episode, session: Session) -> EpisodeResponse:
    """Converteer een Episode model naar EpisodeResponse met tellingen."""
    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode.id)
        .order_by(Scene.scene_number.asc())
    ).all()
    scene_count = len(scenes)

    render_job = session.exec(
        select(RenderJob)
        .where(RenderJob.episode_id == episode.id)
        .where(RenderJob.status == "complete")
        .order_by(RenderJob.completed_at.desc())  # type: ignore[attr-defined]
    ).first()
    render_url = None
    if render_job and render_job.output_path:
        render_url = to_media_url(render_job.output_path)

    publish_job = session.exec(
        select(PublishJob)
        .where(PublishJob.episode_id == episode.id)
        .where(PublishJob.youtube_video_id.is_not(None))
        .order_by(PublishJob.completed_at.desc())  # type: ignore[attr-defined]
    ).first()
    youtube_video_id = (
        publish_job.youtube_video_id if publish_job else episode.youtube_video_id
    )
    youtube_url = publish_job.youtube_url if publish_job else None
    if not youtube_url and youtube_video_id:
        youtube_url = f"https://www.youtube.com/watch?v={youtube_video_id}"

    guardrail_report = guardrails_service.evaluate_episode(
        scenes, episode.target_duration_seconds
    )

    return EpisodeResponse(
        id=episode.id,
        project_id=episode.project_id,
        title=episode.title,
        description=episode.description,
        episode_number=episode.episode_number,
        target_duration_seconds=episode.target_duration_seconds,
        target_duration=episode.target_duration_seconds,
        script_raw=episode.script_raw,
        script_final=episode.script_final,
        seo_title=episode.seo_title,
        seo_description=episode.seo_description,
        seo_tags=episode.seo_tags,
        thumbnail_prompt=episode.thumbnail_prompt,
        thumbnail_path=to_media_url(episode.thumbnail_path),
        target_audience=episode.target_audience or "kids",
        made_for_kids=episode.made_for_kids,
        bg_music_path=episode.bg_music_path,
        status=episode.status,
        scene_count=scene_count,
        render_url=render_url,
        youtube_url=youtube_url,
        youtube_video_id=youtube_video_id or "",
        guardrail_warnings=[
            issue["message"] for issue in guardrail_report["issues"]
        ],
        created_at=episode.created_at,
        updated_at=episode.updated_at,
    )


@router.get("", response_model=list[EpisodeResponse])
@router.get("/", response_model=list[EpisodeResponse])
async def list_episodes(
    project_id: str,
    session: Session = Depends(get_session),
):
    """Lijst alle afleveringen op voor een project."""
    _verify_project(project_id, session)
    episodes = session.exec(
        select(Episode)
        .where(Episode.project_id == project_id)
        .order_by(Episode.episode_number)
    ).all()
    return [_episode_to_response(ep, session) for ep in episodes]


@router.post("", response_model=EpisodeResponse, status_code=201)
@router.post("/", response_model=EpisodeResponse, status_code=201)
async def create_episode(
    project_id: str,
    data: EpisodeCreate,
    session: Session = Depends(get_session),
):
    """Maak een nieuwe aflevering aan voor een project."""
    _verify_project(project_id, session)
    episode = Episode(
        project_id=project_id,
        title=data.title,
        description=data.description,
        episode_number=data.episode_number,
        target_duration_seconds=data.target_duration_seconds,
    )
    session.add(episode)
    session.commit()
    session.refresh(episode)
    return _episode_to_response(episode, session)


@router.get("/{episode_id}", response_model=EpisodeResponse)
async def get_episode(
    project_id: str,
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Haal een aflevering op met scènetelling."""
    _verify_project(project_id, session)
    episode = session.get(Episode, episode_id)
    if episode is None or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")
    return _episode_to_response(episode, session)


@router.put("/{episode_id}", response_model=EpisodeResponse)
async def update_episode(
    project_id: str,
    episode_id: str,
    data: EpisodeUpdate,
    session: Session = Depends(get_session),
):
    """Werk een aflevering bij (auto-save vanuit het frontend)."""
    _verify_project(project_id, session)
    episode = session.get(Episode, episode_id)
    if episode is None or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    update_data = data.model_dump(exclude_unset=True)
    if "target_duration" in update_data and "target_duration_seconds" not in update_data:
        update_data["target_duration_seconds"] = update_data.pop("target_duration")
    for field_name, value in update_data.items():
        setattr(episode, field_name, value)
    episode.updated_at = datetime.now(timezone.utc)

    session.add(episode)
    session.commit()
    session.refresh(episode)
    return _episode_to_response(episode, session)


@router.delete("/{episode_id}")
async def delete_episode(
    project_id: str,
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Verwijder een aflevering en alle gerelateerde data (cascade)."""
    _verify_project(project_id, session)
    episode = session.get(Episode, episode_id)
    if episode is None or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")
    session.delete(episode)
    session.commit()
    return {"detail": f"Aflevering '{episode.title}' verwijderd."}


@router.post("/{episode_id}/generate-script")
async def generate_script(
    project_id: str,
    episode_id: str,
    request: ScriptGenerateRequest,
    session: Session = Depends(get_session),
):
    """Genereer een script via Gemini (achtergrondtaak).

    Returns:
        task_id voor SSE voortgang tracking.
    """
    _verify_project(project_id, session)
    episode = session.get(Episode, episode_id)
    if episode is None or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    task_id = f"script-{episode_id}-{uuid.uuid4().hex[:8]}"

    # Kopieer benodigde data voor de achtergrondtaak
    ep_id = episode.id

    async def _generate():
        from app.services.ai_router import ai_router

        task_manager.update_progress(task_id, 0.1, "Script generatie gestart...")
        task_manager.update_progress(task_id, 0.2, "Script schrijven met gekozen AI-schrijver...")

        chars_list = [{"name": c} for c in (request.characters or [])]
        result = await ai_router.generate_script(
            topic=request.topic,
            target_audience="kids" if (request.target_age_max or 7) <= 7 else "general",
            characters=chars_list,
            scene_count=max(3, int((request.duration_minutes or 2.0) * 3)),
        )

        task_manager.update_progress(task_id, 0.7, "Script en scènes opslaan...")
        persisted = persist_script_result(ep_id, result)
        task_manager.update_progress(task_id, 1.0, "Script generatie voltooid")
        return persisted

    task_manager.start_task(task_id, _generate())
    return {"task_id": task_id, "detail": "Script generatie gestart."}


@router.post("/{episode_id}/generate-seo")
async def generate_seo(
    project_id: str,
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Genereer SEO metadata (titel, beschrijving, tags) voor een aflevering."""
    _verify_project(project_id, session)
    episode = session.get(Episode, episode_id)
    if episode is None or episode.project_id != project_id:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    if not episode.script_final:
        raise HTTPException(
            status_code=400,
            detail="Er is nog geen script beschikbaar. Genereer eerst een script.",
        )

    try:
        from app.services.gemini_service import gemini_service

        seo = await gemini_service.generate_seo(
            title=episode.title,
            description=episode.description,
            script=episode.script_final,
        )

        episode.seo_title = seo.get("seo_title", episode.seo_title)
        episode.seo_description = seo.get("seo_description", episode.seo_description)
        tags = seo.get("seo_tags", [])
        episode.seo_tags = ", ".join(tags) if isinstance(tags, list) else str(tags or "")
        episode.thumbnail_prompt = seo.get("thumbnail_prompt", episode.thumbnail_prompt)
        episode.updated_at = datetime.now(timezone.utc)

        session.add(episode)
        session.commit()
        session.refresh(episode)

        return {
            "seo_title": episode.seo_title,
            "seo_description": episode.seo_description,
            "seo_tags": episode.seo_tags,
            "thumbnail_prompt": episode.thumbnail_prompt,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("SEO generatie mislukt: %s", exc)
        raise HTTPException(status_code=500, detail=f"SEO generatie mislukt: {exc}")
