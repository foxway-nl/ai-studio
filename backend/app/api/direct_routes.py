"""Directe REST routes voor compatibiliteit met het frontend client API.

Biedt directe endpoints voor karakters, afleveringen en instellingen
zonder geneste prefixen.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select, func

from app.core.config import settings
from app.core.database import get_engine, get_session
from app.core.settings_manager import settings_manager
from app.models.models import (
    AppSetting,
    Character,
    CharacterExpression,
    Episode,
    Project,
    PublishJob,
    RenderJob,
    Scene,
)
from app.schemas.schemas import (
    CharacterCreate,
    CharacterResponse,
    CharacterUpdate,
    EpisodeCreate,
    EpisodeResponse,
    EpisodeUpdate,
    ExpressionResponse,
)
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Direct Endpoints"])


# ─────────────────────────────────────────────────────────────
# Karakters (Direct)
# ─────────────────────────────────────────────────────────────


def _char_to_res(character: Character) -> CharacterResponse:
    def _url(path: Optional[str]) -> Optional[str]:
        if not path:
            return None
        return f"/media/characters/{character.id}/{Path(path).name}"

    expressions = [
        ExpressionResponse(
            id=expr.id,
            name=expr.name,
            image_path=expr.image_path,
            image_url=_url(expr.image_path),
            mouth_open_path=expr.mouth_open_path,
            mouth_open_url=_url(expr.mouth_open_path),
            mouth_closed_path=expr.mouth_closed_path,
            mouth_closed_url=_url(expr.mouth_closed_path),
            created_at=expr.created_at,
        )
        for expr in character.expressions
    ]

    sprite_url = None
    if character.sprite_base_path:
        sprite_path = Path(character.sprite_base_path)
        if sprite_path.is_dir():
            candidate = sprite_path / "sprite_base.png"
            if candidate.exists():
                sprite_url = f"/media/characters/{character.id}/{candidate.name}"
        elif sprite_path.exists():
            sprite_url = f"/media/characters/{character.id}/{sprite_path.name}"
    if not sprite_url and expressions:
        sprite_url = expressions[0].image_url

    reference_images: list[str] = []
    try:
        reference_images = json.loads(character.reference_images_json or "[]")
    except Exception:
        reference_images = []

    return CharacterResponse(
        id=character.id,
        project_id=character.project_id,
        name=character.name,
        description=character.description,
        personality=character.personality,
        voice_id=character.voice_id,
        voice_provider=character.voice_provider,
        sprite_base_path=character.sprite_base_path,
        sprite_url=sprite_url,
        style_prompt=character.style_prompt,
        color_palette=character.color_palette,
        reference_images=reference_images,
        expressions=expressions,
        created_at=character.created_at,
        updated_at=character.updated_at,
    )


class DirectCharacterCreate(BaseModel):
    project_id: str
    name: str
    description: str = ""
    personality: str = ""
    voice_id: str = ""
    style_prompt: str = ""


@router.get("/api/characters/{id}", response_model=CharacterResponse)
async def direct_get_character(id: str, session: Session = Depends(get_session)):
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")
    return _char_to_res(char)


@router.post("/api/characters", response_model=CharacterResponse, status_code=201)
async def direct_create_character(data: DirectCharacterCreate, session: Session = Depends(get_session)):
    project = session.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    char = Character(
        project_id=data.project_id,
        name=data.name,
        description=data.description,
        personality=data.personality,
        voice_id=data.voice_id,
        style_prompt=data.style_prompt,
    )
    session.add(char)
    session.commit()
    session.refresh(char)
    return _char_to_res(char)


@router.put("/api/characters/{id}", response_model=CharacterResponse)
async def direct_update_character(id: str, data: CharacterUpdate, session: Session = Depends(get_session)):
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    up = data.model_dump(exclude_unset=True)
    for k, v in up.items():
        if hasattr(char, k) and v is not None:
            setattr(char, k, v)
    char.updated_at = datetime.now(timezone.utc)
    session.add(char)
    session.commit()
    session.refresh(char)
    return _char_to_res(char)


@router.delete("/api/characters/{id}")
async def direct_delete_character(id: str, session: Session = Depends(get_session)):
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")
    session.delete(char)
    session.commit()
    return {"detail": "Karakter verwijderd."}


@router.post("/api/characters/{id}/generate-sprite")
async def direct_generate_sprite(id: str, session: Session = Depends(get_session)):
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    task_id = f"sprite_{id}_{uuid.uuid4().hex[:6]}"
    character_description = char.description or char.name
    character_style = char.style_prompt or "3d Pixar character sprite"

    async def _gen():
        from app.services.image_service import image_service

        task_manager.update_progress(task_id, 0.1, "Karakter sprite initialiseren...")
        out_dir = settings.characters_dir / id
        out_dir.mkdir(parents=True, exist_ok=True)

        task_manager.update_progress(task_id, 0.4, "Sprite renderen en achtergrond uitsnijden...")
        res = await image_service.generate_character_sprite(
            description=character_description,
            style_prompt=character_style,
            output_dir=str(out_dir),
        )

        task_manager.update_progress(task_id, 0.9, "Sprite opslaan...")
        engine = get_engine()
        with Session(engine) as db:
            c = db.get(Character, id)
            if c:
                c.sprite_base_path = res.get("sprite_path")
                c.updated_at = datetime.now(timezone.utc)
                db.add(c)
                db.commit()

        task_manager.update_progress(task_id, 1.0, "Sprite klaar!")
        return res

    task_manager.start_task(task_id, _gen())
    return {"task_id": task_id, "detail": "Sprite generatie gestart."}


@router.post(
    "/api/characters/{id}/expressions",
    response_model=ExpressionResponse,
    status_code=201,
)
async def direct_upload_expression(
    id: str,
    name: str = "neutral",
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    if file.content_type and file.content_type not in {
        "image/png",
        "image/jpeg",
        "image/webp",
    }:
        raise HTTPException(
            status_code=400,
            detail=f"Ongeldig bestandstype: {file.content_type}",
        )

    char_dir = settings.characters_dir / id
    char_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename).suffix if file.filename else ".png"
    dest = char_dir / f"{name}_{uuid.uuid4().hex[:6]}{ext}"
    content = await file.read()
    dest.write_bytes(content)

    expr = CharacterExpression(
        character_id=id,
        name=name,
        image_path=str(dest),
    )
    session.add(expr)
    session.commit()
    session.refresh(expr)

    image_url = f"/media/characters/{id}/{dest.name}"
    return ExpressionResponse(
        id=expr.id,
        name=expr.name,
        image_path=expr.image_path,
        image_url=image_url,
        mouth_open_path=expr.mouth_open_path,
        mouth_open_url=None,
        mouth_closed_path=expr.mouth_closed_path,
        mouth_closed_url=None,
        created_at=expr.created_at,
    )


# ─────────────────────────────────────────────────────────────
# Afleveringen (Direct)
# ─────────────────────────────────────────────────────────────


def _ep_to_res(episode: Episode, session: Session) -> EpisodeResponse:
    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode.id)
        .order_by(Scene.scene_number.asc())
    ).all()

    render_job = session.exec(
        select(RenderJob)
        .where(RenderJob.episode_id == episode.id)
        .where(RenderJob.status == "complete")
        .order_by(RenderJob.completed_at.desc())  # type: ignore[attr-defined]
    ).first()
    render_url = None
    if render_job and render_job.output_path:
        output = render_job.output_path
        render_url = (
            output
            if output.startswith("/media/")
            else f"/media/renders/{Path(output).name}"
        )

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

    from app.services.guardrails_service import guardrails_service

    report = guardrails_service.evaluate_episode(
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
        thumbnail_path=episode.thumbnail_path,
        bg_music_path=episode.bg_music_path,
        status=episode.status,
        scene_count=len(scenes),
        render_url=render_url,
        youtube_url=youtube_url,
        youtube_video_id=youtube_video_id or "",
        guardrail_warnings=[issue["message"] for issue in report["issues"]],
        created_at=episode.created_at,
        updated_at=episode.updated_at,
    )


class DirectEpisodeCreate(BaseModel):
    project_id: str
    title: str
    description: str = ""


@router.get("/api/episodes/{id}", response_model=EpisodeResponse)
async def direct_get_episode(id: str, session: Session = Depends(get_session)):
    ep = session.get(Episode, id)
    if not ep:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")
    return _ep_to_res(ep, session)


@router.post("/api/episodes", response_model=EpisodeResponse, status_code=201)
async def direct_create_episode(data: DirectEpisodeCreate, session: Session = Depends(get_session)):
    project = session.get(Project, data.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project niet gevonden.")

    count = session.exec(select(func.count(Episode.id)).where(Episode.project_id == data.project_id)).one()
    ep = Episode(
        project_id=data.project_id,
        title=data.title,
        description=data.description,
        episode_number=count + 1,
    )
    session.add(ep)
    session.commit()
    session.refresh(ep)
    return _ep_to_res(ep, session)


@router.put("/api/episodes/{id}", response_model=EpisodeResponse)
async def direct_update_episode(id: str, data: EpisodeUpdate, session: Session = Depends(get_session)):
    ep = session.get(Episode, id)
    if not ep:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    up = data.model_dump(exclude_unset=True)
    if "target_duration" in up and "target_duration_seconds" not in up:
        up["target_duration_seconds"] = up.pop("target_duration")
    for k, v in up.items():
        if hasattr(ep, k) and v is not None:
            setattr(ep, k, v)
    ep.updated_at = datetime.now(timezone.utc)
    session.add(ep)
    session.commit()
    session.refresh(ep)
    return _ep_to_res(ep, session)


@router.delete("/api/episodes/{id}")
async def direct_delete_episode(id: str, session: Session = Depends(get_session)):
    ep = session.get(Episode, id)
    if not ep:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")
    session.delete(ep)
    session.commit()
    return {"detail": "Aflevering verwijderd."}


# ─────────────────────────────────────────────────────────────
# Instellingen & Services Status (Direct voor frontend store)
# ─────────────────────────────────────────────────────────────


@router.get("/api/settings")
async def direct_get_settings():
    """Haal instellingen op als key-value mapping (geheimen gemaskeerd)."""
    all_s = settings_manager.get_all()
    return {
        "gemini_api_key": settings_manager.get_masked("gemini_api_key") or "",
        "gemini_api_key_set": bool(all_s.get("gemini_api_key")),
        "ollama_url": all_s.get("ollama_base_url", settings.ollama_base_url),
        "sd_webui_url": all_s.get("sd_webui_base_url", settings.sd_webui_base_url),
        "piper_path": all_s.get("piper_model_path", settings.piper_model_path),
        "kokoro_url": all_s.get("kokoro_base_url", settings.kokoro_base_url),
        "youtube_client_id": all_s.get("youtube_client_id", settings.youtube_client_id),
        "youtube_client_secret": settings_manager.get_masked("youtube_client_secret") or "",
        "youtube_client_secret_set": bool(all_s.get("youtube_client_secret")),
        "youtube_connected": bool(all_s.get("youtube_oauth_token")),
    }


@router.put("/api/settings")
async def direct_save_settings(data: Dict[str, Any]):
    """Sla gewijzigde instellingen op; gemaskeerde waarden worden genegeerd."""
    key_mapping = {
        "gemini_api_key": "gemini_api_key",
        "ollama_url": "ollama_base_url",
        "sd_webui_url": "sd_webui_base_url",
        "piper_path": "piper_model_path",
        "kokoro_url": "kokoro_base_url",
        "youtube_client_id": "youtube_client_id",
        "youtube_client_secret": "youtube_client_secret",
    }
    for frontend_k, val in data.items():
        if val is None:
            continue
        text_value = str(val)
        if "****" in text_value:
            # Gemaskeerde bestaande sleutels nooit overschrijven.
            continue
        backend_k = key_mapping.get(frontend_k, frontend_k)
        settings_manager.set(backend_k, text_value)
    return await direct_get_settings()


@router.get("/api/settings/status")
async def direct_get_services_status():
    """Status van alle externe AI koppelingen."""
    from app.api.setup import _SERVICE_CHECKERS

    results = []
    for name, checker in _SERVICE_CHECKERS.items():
        st = await checker()
        results.append(
            {
                "name": st.name,
                "connected": st.connected,
                "message": st.error or st.instructions_nl or "Gereed",
            }
        )
    return results


@router.post("/api/settings/test/{service}")
async def direct_test_service(service: str):
    """Test verbinding met een specifieke service."""
    from app.api.setup import _SERVICE_CHECKERS

    checker = _SERVICE_CHECKERS.get(service.lower())
    if not checker:
        return {"service": service, "connected": False, "message": f"Onbekende service: {service}"}
    st = await checker()
    return {
        "service": service,
        "connected": st.connected,
        "message": "Verbinding geslaagd!" if st.connected else (st.error or "Verbinding mislukt"),
    }

