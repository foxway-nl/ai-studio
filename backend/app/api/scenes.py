"""Scenes API router – CRUD en beheer van scènes binnen een aflevering."""

import json
import logging
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.models import Episode, Scene
from app.schemas.schemas import (
    EpisodeGuardrailsResponse,
    GuardrailIssue,
    SceneCreate,
    SceneHistoryItem,
    SceneResponse,
    SceneUpdate,
)
from app.services.guardrails_service import guardrails_service
from app.services.script_service import recalculate_timings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Scenes"])


class SceneReorderItem(BaseModel):
    scene_id: str
    order: int


class SelectImagePayload(BaseModel):
    path: str


def _image_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"/media/images/{Path(path).name}"


def _audio_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return f"/media/audio/{Path(path).name}"


def _parse_json_list(raw: str) -> list:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _history_items(raw: str) -> List[SceneHistoryItem]:
    items: List[SceneHistoryItem] = []
    for entry in _parse_json_list(raw):
        if not isinstance(entry, dict) or not entry.get("path"):
            continue
        items.append(
            SceneHistoryItem(
                path=entry["path"],
                url=entry.get("url") or _image_url(entry["path"]),
                prompt=entry.get("prompt", ""),
                created_at=entry.get("created_at", ""),
            )
        )
    return items


def _scene_to_response(scene: Scene) -> SceneResponse:
    img_url = _image_url(scene.composite_image_path or scene.background_image_path)
    aud_url = _audio_url(scene.audio_path)
    char_ids_list = [
        c.strip() for c in (scene.character_ids or "").split(",") if c.strip()
    ]

    return SceneResponse(
        id=scene.id,
        episode_id=scene.episode_id,
        scene_number=scene.scene_number,
        order=scene.scene_number,
        title=scene.title,
        chapter_type=scene.chapter_type,
        speaker=scene.speaker,
        narration_text=scene.narration_text,
        narration=scene.narration_text,
        phonetic_text=scene.phonetic_text,
        visual_prompt=scene.visual_prompt,
        background_prompt=scene.background_prompt,
        image_prompt=scene.image_prompt,
        character_ids=char_ids_list,
        character_positions=scene.character_positions,
        use_2d_sprite=scene.use_2d_sprite,
        sprite_config_json=scene.sprite_config_json,
        animation_type=scene.animation_type,
        transition_type=scene.transition_type,
        sfx_track=scene.sfx_track,
        duration_seconds=scene.duration_seconds,
        duration=scene.duration_seconds,
        pause_after_sec=scene.pause_after_sec,
        background_image_path=scene.background_image_path,
        composite_image_path=scene.composite_image_path,
        image_url=img_url,
        image_history=_history_items(scene.image_history_json),
        audio_path=scene.audio_path,
        audio_url=aud_url,
        word_timestamps=_parse_json_list(scene.word_timestamps),
        start_time=scene.start_time,
        status=scene.status,
        guardrail_warnings=guardrails_service.evaluate_scene(scene),
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


# ─── Scènes ophalen per aflevering ──────────────────────────────────────────


@router.get("/api/episodes/{episode_id}/scenes", response_model=List[SceneResponse])
async def list_scenes_for_episode(
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Haal alle scènes van een aflevering op, gesorteerd op volgorde."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .order_by(Scene.scene_number.asc())
    ).all()
    return [_scene_to_response(s) for s in scenes]


@router.get(
    "/api/episodes/{episode_id}/guardrails",
    response_model=EpisodeGuardrailsResponse,
)
async def get_episode_guardrails(
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Volledig guardrails-rapport voor de aflevering en alle scènes."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .order_by(Scene.scene_number.asc())
    ).all()
    report = guardrails_service.evaluate_episode(
        scenes, episode.target_duration_seconds
    )
    return EpisodeGuardrailsResponse(
        passed=report["passed"],
        safety_score=report["safety_score"],
        total_duration_seconds=report["total_duration_seconds"],
        scene_count=report["scene_count"],
        issues=[GuardrailIssue(**issue) for issue in report["issues"]],
    )


# ─── Scène aanmaken ──────────────────────────────────────────────────────────


@router.post("/api/scenes", response_model=SceneResponse, status_code=201)
@router.post(
    "/api/episodes/{episode_id}/scenes", response_model=SceneResponse, status_code=201
)
async def create_scene(
    data: SceneCreate,
    episode_id: Optional[str] = None,
    session: Session = Depends(get_session),
):
    """Maak een nieuwe scène aan."""
    target_ep_id = episode_id or data.episode_id
    if not target_ep_id:
        raise HTTPException(status_code=400, detail="episode_id is verplicht.")

    episode = session.get(Episode, target_ep_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    existing = session.exec(
        select(Scene).where(Scene.episode_id == target_ep_id)
    ).all()
    num = data.order or data.scene_number
    sc_num = num if num and num > 0 else (len(existing) + 1)

    narr = data.narration or data.narration_text or ""
    dur = data.duration or data.duration_seconds or 8.0

    char_ids = data.character_ids
    if isinstance(char_ids, list):
        char_ids = ",".join(str(c) for c in char_ids)
    elif char_ids is None:
        char_ids = ""

    scene = Scene(
        episode_id=target_ep_id,
        scene_number=sc_num,
        title=data.title,
        chapter_type=data.chapter_type,
        speaker=data.speaker,
        narration_text=narr,
        phonetic_text=data.phonetic_text,
        visual_prompt=data.visual_prompt,
        background_prompt=data.background_prompt,
        image_prompt=data.image_prompt,
        character_ids=char_ids,
        character_positions=data.character_positions,
        use_2d_sprite=data.use_2d_sprite,
        sprite_config_json=data.sprite_config_json,
        animation_type=data.animation_type,
        transition_type=data.transition_type,
        sfx_track=data.sfx_track,
        duration_seconds=dur,
        pause_after_sec=data.pause_after_sec or 0.4,
        status="draft",
    )
    session.add(scene)
    session.commit()
    session.refresh(scene)
    return _scene_to_response(scene)


# ─── Individuele scène opvragen, bewerken en verwijderen ───────────────────────


@router.get("/api/scenes/{scene_id}", response_model=SceneResponse)
async def get_scene(scene_id: str, session: Session = Depends(get_session)):
    """Haal details van één scène op."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")
    return _scene_to_response(scene)


@router.put("/api/scenes/{scene_id}", response_model=SceneResponse)
async def update_scene(
    scene_id: str,
    data: SceneUpdate,
    session: Session = Depends(get_session),
):
    """Werk een scène bij (auto-save vanuit Episode Studio)."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    update_dict = data.model_dump(exclude_unset=True)
    if "narration" in update_dict and "narration_text" not in update_dict:
        update_dict["narration_text"] = update_dict.pop("narration")
    if "order" in update_dict and "scene_number" not in update_dict:
        update_dict["scene_number"] = update_dict.pop("order")
    if "duration" in update_dict and "duration_seconds" not in update_dict:
        update_dict["duration_seconds"] = update_dict.pop("duration")
    if "character_ids" in update_dict and isinstance(
        update_dict["character_ids"], list
    ):
        update_dict["character_ids"] = ",".join(
            str(c) for c in update_dict["character_ids"]
        )

    for key, value in update_dict.items():
        if hasattr(scene, key) and value is not None:
            setattr(scene, key, value)
    scene.updated_at = datetime.now(timezone.utc)

    session.add(scene)
    session.commit()
    session.refresh(scene)
    return _scene_to_response(scene)


@router.delete("/api/scenes/{scene_id}")
async def delete_scene(scene_id: str, session: Session = Depends(get_session)):
    """Verwijder een scène."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")
    session.delete(scene)
    session.commit()
    return {"detail": "Scène verwijderd."}


# ─── Scène volgorde aanpassen ──────────────────────────────────────────────────


@router.put(
    "/api/episodes/{episode_id}/scenes/reorder",
    response_model=List[SceneResponse],
)
@router.post(
    "/api/episodes/{episode_id}/scenes/reorder",
    response_model=List[SceneResponse],
)
async def reorder_scenes(
    episode_id: str,
    order: List[SceneReorderItem],
    session: Session = Depends(get_session),
):
    """Pas de volgorde van de scènes aan (drag & drop)."""
    for item in order:
        scene = session.get(Scene, item.scene_id)
        if scene and scene.episode_id == episode_id:
            scene.scene_number = item.order
            scene.updated_at = datetime.now(timezone.utc)
            session.add(scene)
    session.commit()

    recalculate_timings(episode_id)
    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .order_by(Scene.scene_number.asc())
    ).all()
    return [_scene_to_response(s) for s in scenes]


# ─── Scène-afbeeldingen (geschiedenis) ────────────────────────────────────────


@router.get("/api/scenes/{scene_id}/images")
async def list_scene_images(
    scene_id: str,
    session: Session = Depends(get_session),
):
    """Haal de huidige afbeelding en de geschiedenis van een scène op."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")
    return {
        "scene_id": scene.id,
        "current": _image_url(
            scene.composite_image_path or scene.background_image_path
        ),
        "history": _history_items(scene.image_history_json),
    }


@router.post("/api/scenes/{scene_id}/select-image", response_model=SceneResponse)
async def select_scene_image(
    scene_id: str,
    payload: SelectImagePayload,
    session: Session = Depends(get_session),
):
    """Kies een eerdere afbeelding uit de scène-geschiedenis."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    requested = payload.path
    if requested.startswith("/media/images/"):
        candidate = settings.images_dir / Path(requested).name
    else:
        candidate = Path(requested)
    if not candidate.exists():
        raise HTTPException(status_code=404, detail="Afbeelding niet gevonden.")

    history = _parse_json_list(scene.image_history_json)
    previous = scene.composite_image_path or scene.background_image_path
    if previous:
        history.insert(
            0,
            {
                "path": previous,
                "url": _image_url(previous),
                "prompt": scene.image_prompt,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    scene.composite_image_path = str(candidate)
    scene.background_image_path = str(candidate)
    scene.image_history_json = json.dumps(history[:20], ensure_ascii=False)
    scene.updated_at = datetime.now(timezone.utc)
    session.add(scene)
    session.commit()
    session.refresh(scene)
    return _scene_to_response(scene)


# ─── Eigen stemopname uploaden ────────────────────────────────────────────────


@router.post("/api/scenes/{scene_id}/audio/upload", response_model=SceneResponse)
async def upload_scene_audio(
    scene_id: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload een eigen stemopname voor een scène."""
    scene = session.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    allowed = {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/mp4",
        "audio/m4a",
        "audio/ogg",
        "audio/webm",
    }
    if file.content_type not in allowed and not (
        file.filename and Path(file.filename).suffix.lower() in {".mp3", ".wav", ".m4a", ".ogg", ".webm"}
    ):
        raise HTTPException(
            status_code=400,
            detail=f"Ongeldig audiobestandstype: {file.content_type}",
        )

    ext = Path(file.filename).suffix if file.filename else ".wav"
    filename = f"upload_{scene_id}_{uuid.uuid4().hex[:6]}{ext}"
    dest = settings.audio_dir / filename
    dest.write_bytes(await file.read())

    from app.services.audio_service import audio_service

    duration = audio_service.get_audio_duration(str(dest))
    pause_after = float(scene.pause_after_sec or 0.4)
    scene.audio_path = str(dest)
    scene.duration_seconds = max(0.5, duration + pause_after)
    scene.status = "audio_generated" if scene.status == "draft" else "complete"
    scene.updated_at = datetime.now(timezone.utc)
    session.add(scene)
    session.commit()
    session.refresh(scene)
    return _scene_to_response(scene)
