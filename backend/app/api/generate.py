"""Generatie API router – AI taken voor script, afbeeldingen en audio."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_engine, get_session
from app.models.models import Character, Episode, Scene
from app.schemas.schemas import SceneHistoryItem
from app.services.script_service import persist_script_result, resolve_speaker_voice
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/generate", tags=["Generatie"])


class GenerateScriptPayload(BaseModel):
    episode_id: str
    topic: str = Field(min_length=1, max_length=500)
    target_duration: Optional[int] = 720
    character_ids: Optional[List[str]] = []
    additional_instructions: str = ""
    style: str = "educatief en speels"
    language: str = "nl"


class GenerateImagePayload(BaseModel):
    scene_id: str
    prompt: Optional[str] = None
    provider: Optional[str] = None
    width: int = 1920
    height: int = 1080
    use_2d_sprite: Optional[bool] = None
    enhance_prompt: bool = False


class GenerateAudioPayload(BaseModel):
    scene_id: str
    provider: Optional[str] = None
    voice_id: Optional[str] = None
    text: Optional[str] = None


class GenerateImagePromptPayload(BaseModel):
    scene_id: str
    prompt: Optional[str] = None


class GenerateThumbnailPayload(BaseModel):
    provider: str = "sdwebui"
    prompt: Optional[str] = None


from app.services.image_service import to_media_url


def _image_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    p = Path(path)
    if p.exists() and p.stat().st_size > 0:
        return to_media_url(path)
    return to_media_url(path)


def _audio_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    return to_media_url(path)


def _load_history(raw: str) -> List[Dict[str, Any]]:
    try:
        data = json.loads(raw or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _scene_character_config(scene: Scene) -> List[Dict[str, Any]]:
    """Bouw een compositielijst van karakters voor 2.5D sprites."""
    character_ids = [c.strip() for c in (scene.character_ids or "").split(",") if c.strip()]
    if not character_ids:
        return []

    positions: Dict[str, Any] = {}
    for raw in (scene.sprite_config_json, scene.character_positions):
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                positions.update(parsed)
        except Exception:
            continue

    engine = get_engine()
    config: List[Dict[str, Any]] = []
    with Session(engine) as db:
        for index, character_id in enumerate(character_ids):
            character = db.get(Character, character_id)
            if character is None:
                continue

            sprite_path = character.sprite_base_path
            if sprite_path and Path(sprite_path).is_dir():
                candidates = [
                    Path(sprite_path) / "sprite_base.png",
                    Path(sprite_path) / "neutral.png",
                ]
                sprite_path = next(
                    (str(item) for item in candidates if item.exists()), None
                )
            if not sprite_path or not Path(sprite_path).exists():
                # Gebruik de eerst beschikbare expressie als fallback
                for expression in character.expressions:
                    if expression.image_path and Path(expression.image_path).exists():
                        sprite_path = expression.image_path
                        break

            if not sprite_path or not Path(sprite_path).exists():
                continue

            item = positions.get(character_id, {}) if isinstance(positions, dict) else {}
            default_x = 0.25 if index == 0 else 0.75 if index == 1 else 0.5
            config.append(
                {
                    "sprite_path": sprite_path,
                    "x_percent": float(item.get("x_percent", default_x)),
                    "y_percent": float(item.get("y_percent", 0.88)),
                    "scale": float(item.get("scale", 1.0)),
                    "flip_horizontal": bool(item.get("flip_horizontal", False)),
                }
            )
    return config


# ─────────────────────────────────────────────────────────────
# Script
# ─────────────────────────────────────────────────────────────


@router.post("/script")
async def start_script_generation(
    payload: GenerateScriptPayload,
    session: Session = Depends(get_session),
):
    """Start asynchrone AI-scriptgeneratie voor een aflevering."""
    episode = session.get(Episode, payload.episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    project = episode.project
    target_age_min = project.target_age_min if project else 3
    target_age_max = project.target_age_max if project else 7
    duration_minutes = max(5, (payload.target_duration or episode.target_duration_seconds or 720) // 60)

    # Karakternamen vóór de achtergrondtaak ophalen (sessie is dan gesloten).
    char_names: List[str] = []
    for cid in payload.character_ids or []:
        character = session.get(Character, cid)
        if character:
            char_names.append(character.name)

    task_id = f"script_{payload.episode_id}_{uuid.uuid4().hex[:6]}"

    async def _run():
        from app.services.gemini_service import gemini_service
        from app.services.guardrails_service import guardrails_service

        task_manager.update_progress(
            task_id, 0.1, "Onderwerp analyseren en prompt opstellen..."
        )
        script_data = await gemini_service.generate_script(
            topic=payload.topic,
            target_age_min=target_age_min,
            target_age_max=target_age_max,
            duration_minutes=duration_minutes,
            language=payload.language,
            characters=char_names,
            style=payload.style,
            additional_instructions=payload.additional_instructions,
        )

        task_manager.update_progress(
            task_id, 0.65, "Kindveiligheid & guardrails controleren..."
        )
        full_text = " ".join(
            str(scene.get("narration_text", ""))
            for scene in script_data.get("scenes", [])
        )
        safety = guardrails_service.validate_script(
            full_text, target_age_min, target_age_max
        )
        if not safety["passed"]:
            logger.warning(
                "Guardrails waarschuwingen bij script: %s", safety["issues"]
            )

        task_manager.update_progress(
            task_id, 0.85, "Scènes en SEO opslaan in database..."
        )
        result = persist_script_result(payload.episode_id, script_data)
        task_manager.update_progress(
            task_id,
            1.0,
            f"Script en {result.get('scene_count', 0)} scènes succesvol gegenereerd!",
        )
        return {
            "status": "ok",
            "scene_count": result.get("scene_count", 0),
            "safety": safety,
        }

    task_manager.start_task(task_id, _run())
    return {"task_id": task_id}


# ─────────────────────────────────────────────────────────────
# Afbeeldingen
# ─────────────────────────────────────────────────────────────


@router.post("/image")
async def start_image_generation(
    payload: GenerateImagePayload,
    session: Session = Depends(get_session),
):
    """Start asynchrone beeldgeneratie voor een specifieke scène."""
    scene = session.get(Scene, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    # Alles wat de achtergrondtaak nodig heeft vóór de sessie sluit vastleggen.
    char_ids = [c.strip() for c in (scene.character_ids or "").split(",") if c.strip()]
    char_descriptions = []
    for cid in char_ids:
        ch = session.get(Character, cid)
        if ch:
            char_descriptions.append(f"{ch.name} ({ch.description or ch.personality or ch.style_prompt})")

    scene_snapshot = {
        "id": scene.id,
        "title": scene.title,
        "narration_text": scene.narration_text,
        "visual_prompt": scene.visual_prompt,
        "image_prompt": scene.image_prompt,
        "background_prompt": scene.background_prompt,
        "previous_image": scene.composite_image_path or scene.background_image_path,
        "history": _load_history(scene.image_history_json),
        "use_2d_sprite": scene.use_2d_sprite,
        "character_config": _scene_character_config(scene),
        "char_descriptions": char_descriptions,
    }

    task_id = f"img_{payload.scene_id}_{uuid.uuid4().hex[:6]}"

    async def _run():
        from app.services.image_service import image_service

        base_prompt = (
            payload.prompt
            or scene_snapshot["image_prompt"]
            or scene_snapshot["visual_prompt"]
            or scene_snapshot["background_prompt"]
            or scene_snapshot["narration_text"]
            or scene_snapshot["title"]
            or "vrolijke kleurrijke kinderscène"
        )

        use_sprite = (
            payload.use_2d_sprite
            if payload.use_2d_sprite is not None
            else scene_snapshot["use_2d_sprite"]
        )

        # Als 'Volledige AI Scène' (zonder 2.5D sprites), voeg alle karakters samen in de prompt
        if not use_sprite and scene_snapshot.get("char_descriptions"):
            chars_summary = ", ".join(scene_snapshot["char_descriptions"])
            prompt = f"{base_prompt}, featuring characters: {chars_summary}"
        else:
            prompt = base_prompt

        task_manager.update_progress(task_id, 0.15, "Beeldprompt voorbereiden...")
        if payload.enhance_prompt:
            try:
                from app.services.gemini_service import gemini_service

                prompt = await gemini_service.generate_image_prompt(prompt)
            except Exception as exc:
                logger.warning("Prompt-verbetering mislukt: %s", exc)

        task_manager.update_progress(task_id, 0.4, "AI beeld renderen via primaire engine...")
        background_path = await image_service.generate_image(
            prompt=prompt,
            width=payload.width,
            height=payload.height,
            provider=payload.provider,
        )

        composite_path = background_path
        if use_sprite and scene_snapshot["character_config"]:
            task_manager.update_progress(
                task_id, 0.7, "2.5D karakter-sprites compositen..."
            )
            try:
                composite_path = image_service.composite_2_5d_scene(
                    background_path=background_path,
                    characters=scene_snapshot["character_config"],
                )
            except Exception as exc:
                logger.warning("2.5D compositie mislukt: %s", exc)

        task_manager.update_progress(task_id, 0.9, "Afbeelding koppelen aan scène...")
        history = list(scene_snapshot["history"])
        if scene_snapshot["previous_image"]:
            history.insert(
                0,
                {
                    "path": scene_snapshot["previous_image"],
                    "url": _image_url(scene_snapshot["previous_image"]),
                    "prompt": prompt,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                },
            )
        history = history[:20]

        engine = get_engine()
        with Session(engine) as db:
            sc = db.get(Scene, payload.scene_id)
            if sc:
                sc.background_image_path = background_path
                sc.composite_image_path = composite_path
                sc.image_prompt = prompt
                sc.image_history_json = json.dumps(history, ensure_ascii=False)
                sc.status = "image_generated" if sc.status == "draft" else "complete"
                sc.updated_at = datetime.now(timezone.utc)
                db.add(sc)
                db.commit()

        task_manager.update_progress(task_id, 1.0, "Afbeelding gegenereerd!")
        return {
            "image_path": composite_path,
            "image_url": _image_url(composite_path),
            "background_path": background_path,
        }

    task_manager.start_task(task_id, _run())
    return {"task_id": task_id}


@router.post("/image/prompt")
async def generate_image_prompt(
    payload: GenerateImagePromptPayload,
    session: Session = Depends(get_session),
):
    """Vertaal/optimaliseer een scènebeschrijving naar een Engelse beeldprompt."""
    scene = session.get(Scene, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    description = (
        payload.prompt
        or scene.visual_prompt
        or scene.background_prompt
        or scene.narration_text
        or scene.title
    )
    if not description:
        raise HTTPException(status_code=400, detail="Scène bevat geen beschrijving.")

    prompt = ""
    try:
        from app.services.ollama_service import ollama_service

        prompt = await ollama_service.enhance_prompt(description)
    except Exception as exc:
        logger.info("Ollama prompt-verbetering niet beschikbaar: %s", exc)

    if not prompt:
        try:
            from app.services.gemini_service import gemini_service

            prompt = await gemini_service.generate_image_prompt(description)
        except Exception as exc:
            logger.warning("Gemini prompt-verbetering mislukt: %s", exc)
            prompt = description

    scene.image_prompt = prompt
    scene.updated_at = datetime.now(timezone.utc)
    session.add(scene)
    session.commit()
    return {"scene_id": scene.id, "prompt": prompt}


# ─────────────────────────────────────────────────────────────
# Audio
# ─────────────────────────────────────────────────────────────


def _audio_provider_for_speaker(
    db: Session,
    speaker: str,
    episode_id: str,
    requested_provider: Optional[str],
) -> tuple[str, str, str, str]:
    """Bepaal stemprovider, voice-id, pitch en rate, met karakterstem als voorkeur."""
    if requested_provider:
        return requested_provider, "", "+15Hz", "+0%"
    character = resolve_speaker_voice(db, speaker, episode_id)
    if character and character.voice_provider:
        return (
            character.voice_provider,
            character.voice_id or "nl-NL-FennaNeural",
            character.voice_pitch or "+15Hz",
            character.voice_rate or "+0%",
        )
    return "edge_tts", "nl-NL-FennaNeural", "+15Hz", "+0%"


def _audio_provider_for_scene(
    db: Session, scene: Scene, requested_provider: Optional[str]
) -> tuple[str, str, str, str]:
    active_spk = scene.active_speaker or scene.speaker
    return _audio_provider_for_speaker(
        db, active_spk, scene.episode_id, requested_provider
    )


@router.post("/audio")
async def start_audio_generation(
    payload: GenerateAudioPayload,
    session: Session = Depends(get_session),
):
    """Start asynchrone spraaksynthese voor de gesproken tekst van een scène."""
    scene = session.get(Scene, payload.scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scène niet gevonden.")

    text = (
        payload.text
        or scene.phonetic_text
        or scene.narration_text
    ).strip()
    if not text:
        raise HTTPException(status_code=400, detail="Scène bevat geen gesproken tekst.")

    provider, voice_id, pitch, rate = _audio_provider_for_scene(
        session, scene, payload.provider
    )
    if payload.voice_id:
        voice_id = payload.voice_id
    pause_after = float(scene.pause_after_sec or 0.4)
    scene_id = scene.id

    task_id = f"aud_{scene_id}_{uuid.uuid4().hex[:6]}"

    async def _run():
        from app.services.audio_service import audio_service

        task_manager.update_progress(task_id, 0.2, "Stemtekst synthetiseren via TTS...")
        audio_path = await audio_service.generate_tts(
            text=text,
            voice_id=voice_id,
            provider=provider,
            pitch=pitch,
            rate=rate,
            language="nl",
        )

        task_manager.update_progress(
            task_id, 0.6, "Woord-timestamps berekenen voor lip-sync..."
        )
        timestamps = await audio_service.get_word_timestamps(audio_path)
        audio_duration = audio_service.get_audio_duration(audio_path)
        total_duration = max(0.5, audio_duration + pause_after)

        task_manager.update_progress(task_id, 0.9, "Audio koppelen aan scène...")
        engine = get_engine()
        with Session(engine) as db:
            sc = db.get(Scene, scene_id)
            if sc:
                sc.audio_path = audio_path
                sc.word_timestamps = json.dumps(timestamps, ensure_ascii=False)
                sc.duration_seconds = total_duration
                sc.status = "audio_generated" if sc.status == "draft" else "complete"
                sc.updated_at = datetime.now(timezone.utc)
                db.add(sc)
                db.commit()

        task_manager.update_progress(task_id, 1.0, "Audio klaar!")
        return {
            "audio_path": audio_path,
            "audio_url": _audio_url(audio_path),
            "duration": round(total_duration, 2),
            "words": len(timestamps),
        }

    task_manager.start_task(task_id, _run())
    return {"task_id": task_id}


@router.post("/episodes/{episode_id}/audio")
async def start_bulk_audio_generation(
    episode_id: str,
    session: Session = Depends(get_session),
    provider: Optional[str] = None,
):
    """Genereer audio voor alle scènes van een aflevering sequentieel."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    scenes = session.exec(
        select(Scene)
        .where(Scene.episode_id == episode_id)
        .order_by(Scene.scene_number.asc())
    ).all()
    if not scenes:
        raise HTTPException(status_code=400, detail="Aflevering bevat nog geen scènes.")

    # Leg alle scènegegevens vast voordat de request-sessie sluit.
    scene_snapshots = [
        {
            "id": scene.id,
            "scene_number": scene.scene_number,
            "speaker": scene.speaker,
            "text": (scene.phonetic_text or scene.narration_text or "").strip(),
            "pause_after_sec": float(scene.pause_after_sec or 0.4),
        }
        for scene in scenes
    ]
    total = len(scene_snapshots)
    task_id = f"audioall_{episode_id}_{uuid.uuid4().hex[:6]}"

    async def _run():
        from app.services.audio_service import audio_service

        errors: List[str] = []
        generated = 0
        for idx, snapshot in enumerate(scene_snapshots):
            text = snapshot["text"]
            if not text:
                continue

            progress = 0.05 + (0.9 * idx / max(1, total))
            task_manager.update_progress(
                task_id,
                progress,
                f"Audio scène {idx + 1}/{total} genereren...",
            )

            with Session(get_engine()) as db:
                voice_provider, voice_id = _audio_provider_for_speaker(
                    db,
                    snapshot["speaker"],
                    episode_id,
                    provider,
                )
            try:
                audio_path = await audio_service.generate_tts(
                    text=text,
                    voice_id=voice_id,
                    provider=voice_provider,
                    language="nl",
                )
                timestamps = await audio_service.get_word_timestamps(audio_path)
                audio_duration = audio_service.get_audio_duration(audio_path)
                pause_after = snapshot["pause_after_sec"]

                with Session(get_engine()) as db:
                    sc = db.get(Scene, snapshot["id"])
                    if sc:
                        sc.audio_path = audio_path
                        sc.word_timestamps = json.dumps(timestamps, ensure_ascii=False)
                        sc.duration_seconds = max(0.5, audio_duration + pause_after)
                        sc.status = (
                            "audio_generated" if sc.status == "draft" else "complete"
                        )
                        sc.updated_at = datetime.now(timezone.utc)
                        db.add(sc)
                        db.commit()
                generated += 1
            except Exception as exc:
                logger.exception(
                    "Audio voor scène %s mislukt: %s",
                    snapshot["scene_number"],
                    exc,
                )
                errors.append(f"Scène {snapshot['scene_number']}: {exc}")

        task_manager.update_progress(
            task_id,
            1.0,
            f"Audio voltooid voor {generated}/{total} scènes.",
        )
        if errors:
            return {"status": "partial", "errors": errors, "generated": generated}
        return {"status": "ok", "scene_count": total, "generated": generated}

    task_manager.start_task(task_id, _run())
    return {"task_id": task_id, "scene_count": total}


# ─────────────────────────────────────────────────────────────
# SEO & thumbnail
# ─────────────────────────────────────────────────────────────


@router.post("/episodes/{episode_id}/seo")
async def generate_episode_seo(
    episode_id: str,
    session: Session = Depends(get_session),
):
    """Genereer SEO/GEO metadata voor een aflevering."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")
    if not episode.script_final:
        raise HTTPException(
            status_code=400,
            detail="Er is nog geen script beschikbaar. Genereer eerst een script.",
        )

    from app.services.gemini_service import gemini_service

    try:
        seo = await gemini_service.generate_seo(
            title=episode.title,
            description=episode.description,
            script=episode.script_final,
        )
    except Exception as exc:
        logger.exception("SEO-generatie mislukt: %s", exc)
        raise HTTPException(status_code=500, detail=f"SEO-generatie mislukt: {exc}")

    episode.seo_title = seo.get("seo_title", episode.seo_title)
    episode.seo_description = seo.get("seo_description", episode.seo_description)
    tags = seo.get("seo_tags", [])
    episode.seo_tags = ", ".join(tags) if isinstance(tags, list) else str(tags or "")
    episode.thumbnail_prompt = seo.get(
        "thumbnail_prompt", episode.thumbnail_prompt
    )
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


@router.post("/episodes/{episode_id}/thumbnail")
async def generate_episode_thumbnail(
    episode_id: str,
    payload: GenerateThumbnailPayload,
    session: Session = Depends(get_session),
):
    """Genereer een YouTube-thumbnail op basis van het opgeslagen prompt."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    prompt = payload.prompt or episode.thumbnail_prompt
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail="Geen thumbnail-prompt beschikbaar. Genereer eerst SEO.",
        )

    from app.services.image_service import image_service

    try:
        path = await image_service.generate_image(
            prompt=prompt,
            width=1280,
            height=720,
            provider=payload.provider,
        )
    except Exception as exc:
        logger.exception("Thumbnail-generatie mislukt: %s", exc)
        raise HTTPException(status_code=500, detail=f"Thumbnail mislukt: {exc}")

    episode.thumbnail_path = path
    episode.updated_at = datetime.now(timezone.utc)
    session.add(episode)
    session.commit()
    return {"thumbnail_path": path, "thumbnail_url": _image_url(path)}
