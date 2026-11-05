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
from app.core.settings_manager import SettingsManager, settings_manager
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
    ExportFlowResponse,
    ExpressionResponse,
)
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Direct Endpoints"])


# ─────────────────────────────────────────────────────────────
# Karakters (Direct)
# ─────────────────────────────────────────────────────────────


from app.services.image_service import to_media_url


def _char_to_res(character: Character) -> CharacterResponse:
    expressions = [
        ExpressionResponse(
            id=expr.id,
            name=expr.name,
            image_path=expr.image_path,
            image_url=to_media_url(expr.image_path),
            mouth_open_path=expr.mouth_open_path,
            mouth_open_url=to_media_url(expr.mouth_open_path),
            mouth_closed_path=expr.mouth_closed_path,
            mouth_closed_url=to_media_url(expr.mouth_closed_path),
            created_at=expr.created_at,
        )
        for expr in character.expressions
    ]

    sprite_url = None
    if character.sprite_base_path:
        sprite_path = Path(character.sprite_base_path)
        if sprite_path.is_dir():
            candidate = sprite_path / "sprite_base.png"
            if candidate.exists() and candidate.stat().st_size > 0:
                sprite_url = to_media_url(str(candidate))
        elif sprite_path.exists() and sprite_path.stat().st_size > 0:
            sprite_url = to_media_url(str(sprite_path))
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
        voice_pitch=character.voice_pitch or "+15Hz",
        voice_rate=character.voice_rate or "+0%",
        sprite_base_path=character.sprite_base_path,
        sprite_url=sprite_url,
        style_prompt=character.style_prompt,
        visual_dna_prompt=character.visual_dna_prompt or "",
        color_palette=character.color_palette,
        reference_images=reference_images,
        reference_image_urls=[to_media_url(p) for p in reference_images if p],
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


@router.post("/api/characters/{id}/upload-reference", response_model=CharacterResponse)
async def direct_upload_character_reference(
    id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload een referentie-afbeelding voor het consistente karakter uiterlijk."""
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    ext = Path(file.filename or "ref.png").suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp"}:
        ext = ".png"

    filename = f"ref_{id}_{int(datetime.now(timezone.utc).timestamp())}_{uuid.uuid4().hex[:4]}{ext}"
    dest = settings.characters_dir / filename
    dest.write_bytes(await file.read())

    try:
        current_refs = json.loads(char.reference_images_json or "[]")
        if not isinstance(current_refs, list):
            current_refs = []
    except Exception:
        current_refs = []

    if len(current_refs) >= 3:
        current_refs.pop(0)
    current_refs.append(str(dest))

    char.reference_images_json = json.dumps(current_refs, ensure_ascii=False)
    char.updated_at = datetime.now(timezone.utc)
    session.add(char)
    session.commit()
    session.refresh(char)
    return _char_to_res(char)


@router.delete("/api/characters/{id}/reference/{index}", response_model=CharacterResponse)
async def direct_delete_character_reference(
    id: str,
    index: int,
    session: Session = Depends(get_session),
):
    """Verwijder een referentie-afbeelding van een karakter."""
    char = session.get(Character, id)
    if not char:
        raise HTTPException(status_code=404, detail="Karakter niet gevonden.")

    try:
        current_refs = json.loads(char.reference_images_json or "[]")
        if not isinstance(current_refs, list):
            current_refs = []
    except Exception:
        current_refs = []

    if 0 <= index < len(current_refs):
        current_refs.pop(index)
        char.reference_images_json = json.dumps(current_refs, ensure_ascii=False)
        char.updated_at = datetime.now(timezone.utc)
        session.add(char)
        session.commit()
        session.refresh(char)

    return _char_to_res(char)


@router.post("/api/characters/{id}/generate-sprite")
async def direct_generate_sprite(
    id: str,
    emotion: str = "blij",
    session: Session = Depends(get_session),
):
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

        task_manager.update_progress(task_id, 0.4, f"Sprite ({emotion}) renderen en mond-sprites maken...")
        res = await image_service.generate_character_sprite(
            description=character_description,
            emotion=emotion,
            style_prompt=character_style,
            output_dir=str(out_dir),
        )

        task_manager.update_progress(task_id, 0.9, "Sprite en expressies opslaan in database...")
        engine = get_engine()
        with Session(engine) as db:
            c = db.get(Character, id)
            if c:
                c.sprite_base_path = res.get("sprite_path")
                c.updated_at = datetime.now(timezone.utc)
                db.add(c)

                # Zoek of maak expressie aan
                expr = db.exec(
                    select(CharacterExpression)
                    .where(CharacterExpression.character_id == id)
                    .where(CharacterExpression.name == emotion)
                ).first()
                if not expr:
                    expr = CharacterExpression(
                        character_id=id,
                        name=emotion,
                        image_path=res.get("sprite_path", ""),
                        mouth_open_path=res.get("mouth_open_path"),
                        mouth_closed_path=res.get("mouth_closed_path"),
                    )
                else:
                    expr.image_path = res.get("sprite_path", "")
                    expr.mouth_open_path = res.get("mouth_open_path")
                    expr.mouth_closed_path = res.get("mouth_closed_path")
                db.add(expr)
                db.commit()

        task_manager.update_progress(task_id, 1.0, "Sprite klaar!")
        return res

    task_manager.start_task(task_id, _gen())
    return {"task_id": task_id, "detail": f"Sprite generatie voor '{emotion}' gestart."}


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
    render_url = to_media_url(render_job.output_path) if (render_job and render_job.output_path) else None

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
        thumbnail_path=to_media_url(episode.thumbnail_path),
        target_audience=episode.target_audience or "kids",
        made_for_kids=episode.made_for_kids,
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


@router.get("/api/episodes/{id}/export-flow", response_model=ExportFlowResponse)
async def direct_export_episode_flow(id: str):
    """Exporteert alle Start-Frames en Motion Prompts als een Google Flow ZIP bestand."""
    from app.services.video_animation_service import video_animation_service
    try:
        res = await video_animation_service.export_episode_flow(id)
        return ExportFlowResponse(
            zip_url=res["zip_url"],
            zip_path=res["zip_path"],
            scene_count=res["scene_count"],
            message=res["message"],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Instellingen & Services Status (Direct voor frontend store)
# ─────────────────────────────────────────────────────────────


@router.get("/api/settings")
async def direct_get_settings():
    """Haal instellingen op als key-value mapping (geheimen gemaskeerd)."""
    all_s = settings_manager.get_all()
    disc_raw = all_s.get("gemini_discovered_models", "")
    disc = {}
    if disc_raw:
        try:
            disc = json.loads(disc_raw)
        except Exception:
            disc = {}

    return {
        "gemini_api_key": settings_manager.get_masked("gemini_api_key") or "",
        "gemini_api_key_set": bool(all_s.get("gemini_api_key")),
        "gemini_model": all_s.get("gemini_model", "gemini-2.5-flash"),
        "gemini_text_model": all_s.get("gemini_text_model", all_s.get("gemini_model", "gemini-2.5-flash")),
        "gemini_image_model": all_s.get("gemini_image_model", "imagen-3.0-generate-002"),
        "gemini_video_model": all_s.get("gemini_video_model", "veo-2.0-generate-001"),
        "discovered_models": disc,
        "default_image_provider": all_s.get("default_image_provider", "gemini"),
        # Groq Cloud
        "groq_api_key": settings_manager.get_masked("groq_api_key") or "",
        "groq_api_key_set": bool(all_s.get("groq_api_key")),
        # Hugging Face
        "hf_token": settings_manager.get_masked("hf_token") or "",
        "hf_token_set": bool(all_s.get("hf_token")),
        "hf_video_space_id": all_s.get("hf_video_space_id", "multimodalart/Wan2.1-Fast"),
        # Taak Router
        "task_script_provider": all_s.get("task_script_provider", "gemini"),
        "task_script_model": all_s.get("task_script_model", "gemini-2.5-flash"),
        "task_prompt_provider": all_s.get("task_prompt_provider", "gemini"),
        "task_prompt_model": all_s.get("task_prompt_model", "gemini-2.5-flash"),
        "task_tts_provider": all_s.get("task_tts_provider", "edge_tts"),
        "task_tts_voice": all_s.get("task_tts_voice", "nl-NL-FennaNeural"),
        "task_whisper_provider": all_s.get("task_whisper_provider", "groq_whisper"),
        "task_image_provider": all_s.get("task_image_provider", "gemini_imagen"),
        "task_image_model": all_s.get("task_image_model", "imagen-3.0-generate-002"),
        "task_video_provider": all_s.get("task_video_provider", "local_2_5d"),
        "task_video_model": all_s.get("task_video_model", "veo-2.0-generate-001"),
        # Overige services
        "wan_api_url": all_s.get("wan_api_url", settings.wan_api_url),
        "wan_api_key": settings_manager.get_masked("wan_api_key") or "",
        "ollama_url": all_s.get("ollama_base_url", settings.ollama_base_url),
        "sd_webui_url": all_s.get("sd_webui_base_url", settings.sd_webui_base_url),
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
        "gemini_model": "gemini_model",
        "gemini_text_model": "gemini_text_model",
        "gemini_image_model": "gemini_image_model",
        "gemini_video_model": "gemini_video_model",
        "default_image_provider": "default_image_provider",
        "groq_api_key": "groq_api_key",
        "hf_token": "hf_token",
        "hf_video_space_id": "hf_video_space_id",
        "task_script_provider": "task_script_provider",
        "task_script_model": "task_script_model",
        "task_prompt_provider": "task_prompt_provider",
        "task_prompt_model": "task_prompt_model",
        "task_tts_provider": "task_tts_provider",
        "task_tts_voice": "task_tts_voice",
        "task_whisper_provider": "task_whisper_provider",
        "task_image_provider": "task_image_provider",
        "task_image_model": "task_image_model",
        "task_video_provider": "task_video_provider",
        "task_video_model": "task_video_model",
        "wan_api_url": "wan_api_url",
        "wan_api_key": "wan_api_key",
        "ollama_url": "ollama_base_url",
        "sd_webui_url": "sd_webui_base_url",
        "youtube_client_id": "youtube_client_id",
        "youtube_client_secret": "youtube_client_secret",
    }
    for frontend_k, val in data.items():
        if val is None:
            continue
        text_value = str(val).strip()
        if SettingsManager.is_masked_value(text_value):
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

