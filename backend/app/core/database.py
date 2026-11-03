"""SQLite database engine en sessie management via SQLModel."""

import logging

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from .config import settings

logger = logging.getLogger(__name__)

_engine = None

# Kolommen die na de eerste release zijn toegevoegd. Omdat SQLite
# `CREATE TABLE IF NOT EXISTS` bestaande tabellen niet aanpast, voegen we
# ontbrekende kolommen hier idempotent toe bij het opstarten.
_SCHEMA_PATCHES: dict[str, dict[str, str]] = {
    "characters": {
        "voice_pitch": "TEXT NOT NULL DEFAULT '+15Hz'",
        "voice_rate": "TEXT NOT NULL DEFAULT '+0%'",
        "style_prompt": "TEXT NOT NULL DEFAULT ''",
        "visual_dna_prompt": "TEXT NOT NULL DEFAULT ''",
        "color_palette": "TEXT NOT NULL DEFAULT ''",
        "reference_images_json": "TEXT NOT NULL DEFAULT '[]'",
    },
    "episodes": {
        "target_audience": "TEXT NOT NULL DEFAULT 'kids'",
        "made_for_kids": "INTEGER NOT NULL DEFAULT 1",
        "bg_music_path": "TEXT NOT NULL DEFAULT ''",
        "youtube_video_id": "TEXT NOT NULL DEFAULT ''",
    },
    "scenes": {
        "chapter_type": "TEXT NOT NULL DEFAULT 'chapter'",
        "speaker": "TEXT NOT NULL DEFAULT ''",
        "phonetic_text": "TEXT NOT NULL DEFAULT ''",
        "image_prompt": "TEXT NOT NULL DEFAULT ''",
        "motion_prompt": "TEXT NOT NULL DEFAULT ''",
        "video_clip_path": "TEXT DEFAULT NULL",
        "animation_engine": "TEXT NOT NULL DEFAULT 'veo'",
        "character_ids": "TEXT NOT NULL DEFAULT ''",
        "characters_in_scene": "TEXT NOT NULL DEFAULT '[]'",
        "character_positions": "TEXT NOT NULL DEFAULT ''",
        "active_speaker": "TEXT NOT NULL DEFAULT 'verteller'",
        "use_2d_sprite": "INTEGER NOT NULL DEFAULT 0",
        "sprite_config_json": "TEXT NOT NULL DEFAULT ''",
        "image_history_json": "TEXT NOT NULL DEFAULT '[]'",
        "sfx_track": "TEXT NOT NULL DEFAULT ''",
        "pause_after_sec": "REAL NOT NULL DEFAULT 0.4",
        "word_timestamps": "TEXT NOT NULL DEFAULT '[]'",
    },
}


def get_engine():
    """Lazy-initialize de database engine (SQLite, single-file)."""
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.resolved_database_url,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def _apply_schema_patches() -> None:
    """Voeg ontbrekende kolommen toe aan bestaande SQLite-tabellen."""
    engine = get_engine()
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as conn:
        for table_name, columns in _SCHEMA_PATCHES.items():
            if table_name not in table_names:
                continue
            existing = {col["name"] for col in inspector.get_columns(table_name)}
            for column_name, definition in columns.items():
                if column_name in existing:
                    continue
                conn.execute(
                    text(
                        f'ALTER TABLE "{table_name}" '
                        f'ADD COLUMN "{column_name}" {definition}'
                    )
                )
                logger.info(
                    "Migratie: kolom %s.%s toegevoegd.", table_name, column_name
                )


def init_db() -> None:
    """Maak alle tabellen aan als ze nog niet bestaan en migreer oude schema's."""
    from app.models import models as _  # noqa: F401 – registreer tabellen

    engine = get_engine()
    SQLModel.metadata.create_all(engine)
    _apply_schema_patches()


def get_session():
    """Yield een database sessie voor dependency injection."""
    engine = get_engine()
    with Session(engine) as session:
        yield session
