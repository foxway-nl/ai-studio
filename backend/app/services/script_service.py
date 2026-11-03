"""Script- en scène-persistentie voor AI-Studio.

Centraliseert het opslaan van een door Gemini gegenereerd script, zodat
zowel de legacy- als de nieuwe generatie-endpoints dezelfde structuur
opleveren (episode metadata + scènes).
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlmodel import Session, select

from app.core.database import get_engine
from app.models.models import Character, Episode, Scene

logger = logging.getLogger(__name__)

# Volgorde van de vaste afleveringsstructuur. Op basis van de positie in het
# script wordt een chapter_type afgeleid wanneer Gemini dit niet meelevert.
_CHAPTER_SEQUENCE = [
    ("hook", 0.06),
    ("intro", 0.10),
    ("chapter", 0.45),
    ("question", 0.55),
    ("chapter", 0.75),
    ("question", 0.80),
    ("chapter", 0.92),
    ("song", 0.96),
    ("outro", 1.0),
]


def infer_chapter_type(index: int, total: int, explicit: Optional[str] = None) -> str:
    """Bepaal het hoofdstuktype op basis van de scènepositie."""
    if explicit:
        return explicit
    if total <= 0:
        return "chapter"
    ratio = (index + 1) / total
    for chapter_type, threshold in _CHAPTER_SEQUENCE:
        if ratio <= threshold:
            return chapter_type
    return "chapter"


def _coerce_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _parse_tags(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return _coerce_text(value)


def persist_script_result(episode_id: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Sla een scriptresultaat op en vervang de bestaande scènes.

    Returns:
        dict met episode_id, scene_count en title.
    """
    scenes_data = result.get("scenes") or []
    if not isinstance(scenes_data, list):
        raise ValueError("Scriptresultaat bevat geen geldige scènes-lijst.")

    engine = get_engine()
    with Session(engine) as db:
        episode = db.get(Episode, episode_id)
        if episode is None:
            raise ValueError("Aflevering niet gevonden.")

        raw_script = result.get("script")
        if not raw_script:
            raw_script = json.dumps(result, ensure_ascii=False)

        episode.title = _coerce_text(result.get("title")) or episode.title
        episode.description = _coerce_text(result.get("synopsis")) or episode.description
        episode.seo_title = _coerce_text(result.get("seo_title")) or episode.title
        episode.seo_description = _coerce_text(result.get("seo_description"))
        episode.seo_tags = _parse_tags(result.get("seo_tags"))
        episode.thumbnail_prompt = _coerce_text(result.get("thumbnail_prompt"))
        episode.script_raw = raw_script
        episode.script_final = " ".join(
            _coerce_text(scene.get("narration_text"))
            for scene in scenes_data
            if scene.get("narration_text")
        )
        episode.status = "scripting"
        episode.updated_at = datetime.now(timezone.utc)
        db.add(episode)

        # Oude scènes verwijderen
        old_scenes = db.exec(select(Scene).where(Scene.episode_id == episode.id)).all()
        for old in old_scenes:
            db.delete(old)
        db.flush()

        total = len(scenes_data)
        for idx, scene_data in enumerate(scenes_data):
            if not isinstance(scene_data, dict):
                continue
            character_ids = scene_data.get("character_ids") or []
            if isinstance(character_ids, list):
                character_ids = ",".join(str(cid) for cid in character_ids)

            scene = Scene(
                episode_id=episode.id,
                scene_number=int(scene_data.get("scene_number", idx + 1) or idx + 1),
                title=_coerce_text(scene_data.get("title")) or f"Scène {idx + 1}",
                chapter_type=infer_chapter_type(
                    idx, total, scene_data.get("chapter_type")
                ),
                speaker=_coerce_text(scene_data.get("speaker")),
                narration_text=_coerce_text(scene_data.get("narration_text")),
                phonetic_text=_coerce_text(scene_data.get("phonetic_text")),
                visual_prompt=_coerce_text(scene_data.get("visual_prompt")),
                background_prompt=_coerce_text(scene_data.get("background_prompt")),
                image_prompt=_coerce_text(
                    scene_data.get("image_prompt")
                    or scene_data.get("visual_prompt")
                ),
                character_ids=character_ids,
                character_positions=json.dumps(
                    scene_data.get("character_positions") or {},
                    ensure_ascii=False,
                )
                if isinstance(scene_data.get("character_positions"), (dict, list))
                else _coerce_text(scene_data.get("character_positions")),
                use_2d_sprite=bool(scene_data.get("use_2d_sprite", False)),
                sprite_config_json=json.dumps(
                    scene_data.get("sprite_config") or {},
                    ensure_ascii=False,
                )
                if isinstance(scene_data.get("sprite_config"), (dict, list))
                else _coerce_text(scene_data.get("sprite_config")),
                animation_type=_coerce_text(
                    scene_data.get("animation_type") or "ken_burns"
                ),
                transition_type=_coerce_text(
                    scene_data.get("transition_type") or "crossfade"
                ),
                sfx_track=_coerce_text(scene_data.get("sfx_track")),
                duration_seconds=float(scene_data.get("duration_seconds", 10.0) or 10.0),
                pause_after_sec=float(scene_data.get("pause_after_sec", 0.4) or 0.4),
                status="draft",
            )
            db.add(scene)

        db.commit()

        # Starttijd van elke scène herberekenen
        recalculate_timings(episode.id)

    return {
        "episode_id": episode_id,
        "scene_count": total,
        "title": result.get("title", ""),
    }


def recalculate_timings(episode_id: str) -> List[Scene]:
    """Herbereken de starttijd van alle scènes op basis van hun duur."""
    engine = get_engine()
    with Session(engine) as db:
        scenes = db.exec(
            select(Scene)
            .where(Scene.episode_id == episode_id)
            .order_by(Scene.scene_number.asc())
        ).all()
        cursor = 0.0
        for scene in scenes:
            scene.start_time = round(cursor, 2)
            scene.duration_seconds = max(
                0.5, float(scene.duration_seconds or 0.5)
            )
            cursor += scene.duration_seconds
            db.add(scene)
        db.commit()
        return list(scenes)


def resolve_speaker_voice(
    db: Session, speaker: str, episode_id: str
) -> Optional[Character]:
    """Zoek het karakter dat als spreker optreedt in een scène."""
    if not speaker:
        return None
    episode = db.get(Episode, episode_id)
    if episode is None:
        return None
    return db.exec(
        select(Character).where(
            Character.project_id == episode.project_id,
            func.lower(Character.name) == speaker.strip().lower(),
        )
    ).first()
