"""SQLModel database tabellen voor AI-Studio.

Alle tabellen worden opgeslagen in een SQLite database in /data/ai_studio.db.
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex


# ─────────────────────────────────────────────────────────────
# Applicatie-instellingen (key-value store)
# ─────────────────────────────────────────────────────────────


class AppSetting(SQLModel, table=True):
    __tablename__ = "app_settings"

    id: Optional[int] = Field(default=None, primary_key=True)
    key: str = Field(index=True, unique=True)
    value: str = ""
    description: str = ""
    updated_at: datetime = Field(default_factory=_utcnow)


# ─────────────────────────────────────────────────────────────
# Project – top-level container voor een videoserie
# ─────────────────────────────────────────────────────────────


class Project(SQLModel, table=True):
    __tablename__ = "projects"

    id: str = Field(default_factory=_new_id, primary_key=True)
    name: str = "Nieuw Project"
    description: str = ""
    target_age_min: int = 3
    target_age_max: int = 7
    language: str = "nl"
    channel_name: str = ""
    thumbnail_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relaties
    episodes: list["Episode"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    characters: list["Character"] = Relationship(
        back_populates="project",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ─────────────────────────────────────────────────────────────
# Karakter – herbruikbaar personage met expressies/sprites
# ─────────────────────────────────────────────────────────────


class Character(SQLModel, table=True):
    __tablename__ = "characters"

    id: str = Field(default_factory=_new_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    name: str = "Nieuw Karakter"
    description: str = ""
    personality: str = ""
    voice_id: str = ""
    voice_provider: str = "piper"  # piper | google | kokoro
    sprite_base_path: Optional[str] = None
    style_prompt: str = ""
    color_palette: str = ""
    reference_images_json: str = "[]"  # JSON array met referentie-afbeeldingen
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relaties
    project: Optional[Project] = Relationship(back_populates="characters")
    expressions: list["CharacterExpression"] = Relationship(
        back_populates="character",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


class CharacterExpression(SQLModel, table=True):
    __tablename__ = "character_expressions"

    id: str = Field(default_factory=_new_id, primary_key=True)
    character_id: str = Field(foreign_key="characters.id", index=True)
    name: str = "neutral"  # blij, verdrietig, verbaasd, boos, etc.
    image_path: str = ""
    mouth_open_path: Optional[str] = None
    mouth_closed_path: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)

    character: Optional[Character] = Relationship(back_populates="expressions")


# ─────────────────────────────────────────────────────────────
# Episode – individuele video aflevering
# ─────────────────────────────────────────────────────────────


class Episode(SQLModel, table=True):
    __tablename__ = "episodes"

    id: str = Field(default_factory=_new_id, primary_key=True)
    project_id: str = Field(foreign_key="projects.id", index=True)
    title: str = "Nieuwe Aflevering"
    description: str = ""
    episode_number: int = 1
    target_duration_seconds: int = 720  # 12 minuten standaard
    script_raw: str = ""
    script_final: str = ""
    seo_title: str = ""
    seo_description: str = ""
    seo_tags: str = ""  # Komma-gescheiden
    thumbnail_prompt: str = ""
    thumbnail_path: Optional[str] = None
    bg_music_path: str = ""
    youtube_video_id: str = ""
    status: str = "draft"  # draft | scripting | scenes | audio | rendering | rendered | published
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    # Relaties
    project: Optional[Project] = Relationship(back_populates="episodes")
    scenes: list["Scene"] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    audio_tracks: list["AudioTrack"] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    render_jobs: list["RenderJob"] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    publish_jobs: list["PublishJob"] = Relationship(
        back_populates="episode",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )


# ─────────────────────────────────────────────────────────────
# Scene – scène binnen een aflevering
# ─────────────────────────────────────────────────────────────


class Scene(SQLModel, table=True):
    __tablename__ = "scenes"

    id: str = Field(default_factory=_new_id, primary_key=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    scene_number: int = 1
    title: str = ""
    chapter_type: str = "chapter"  # hook | intro | chapter | question | song | outro
    speaker: str = ""
    narration_text: str = ""
    phonetic_text: str = ""
    visual_prompt: str = ""
    background_prompt: str = ""
    image_prompt: str = ""
    character_ids: str = ""  # Komma-gescheiden karakter ID's
    character_positions: str = ""  # JSON string met posities
    use_2d_sprite: bool = False
    sprite_config_json: str = ""  # JSON met sprite posities/schalen
    image_history_json: str = "[]"  # JSON array met eerdere afbeeldingen
    animation_type: str = "ken_burns"  # ken_burns | pan_left | pan_right | zoom_in | zoom_out | static
    transition_type: str = "crossfade"  # crossfade | fade_black | slide_left | slide_right | wipe
    sfx_track: str = ""
    duration_seconds: float = 8.0
    pause_after_sec: float = 0.4
    background_image_path: Optional[str] = None
    composite_image_path: Optional[str] = None
    audio_path: Optional[str] = None
    word_timestamps: str = "[]"  # JSON array met woord-timestamps
    start_time: float = 0.0
    status: str = "draft"  # draft | image_generated | audio_generated | complete
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)

    episode: Optional[Episode] = Relationship(back_populates="scenes")


# ─────────────────────────────────────────────────────────────
# AudioTrack – gegenereerde audio bestanden
# ─────────────────────────────────────────────────────────────


class AudioTrack(SQLModel, table=True):
    __tablename__ = "audio_tracks"

    id: str = Field(default_factory=_new_id, primary_key=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    track_type: str = "narration"  # narration | music | sfx
    name: str = ""
    file_path: str = ""
    duration_seconds: float = 0.0
    volume: float = 1.0
    start_time: float = 0.0
    voice_id: str = ""
    voice_provider: str = ""
    word_timestamps: str = ""  # JSON array met woord-timestamps
    status: str = "pending"  # pending | generating | ready | error
    error_message: str = ""
    created_at: datetime = Field(default_factory=_utcnow)

    episode: Optional[Episode] = Relationship(back_populates="audio_tracks")


# ─────────────────────────────────────────────────────────────
# RenderJob – video render taak
# ─────────────────────────────────────────────────────────────


class RenderJob(SQLModel, table=True):
    __tablename__ = "render_jobs"

    id: str = Field(default_factory=_new_id, primary_key=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    status: str = "queued"  # queued | rendering | compositing | normalizing | complete | error
    progress: float = 0.0  # 0.0 – 1.0
    current_step: str = ""
    output_path: Optional[str] = None
    resolution: str = "1920x1080"
    fps: int = 30
    error_message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)

    episode: Optional[Episode] = Relationship(back_populates="render_jobs")


# ─────────────────────────────────────────────────────────────
# PublishJob – YouTube upload taak
# ─────────────────────────────────────────────────────────────


class PublishJob(SQLModel, table=True):
    __tablename__ = "publish_jobs"

    id: str = Field(default_factory=_new_id, primary_key=True)
    episode_id: str = Field(foreign_key="episodes.id", index=True)
    status: str = "pending"  # pending | uploading | processing | published | error
    progress: float = 0.0
    youtube_video_id: Optional[str] = None
    youtube_url: Optional[str] = None
    privacy_status: str = "private"  # private | unlisted | public
    made_for_kids: bool = True
    error_message: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=_utcnow)

    episode: Optional[Episode] = Relationship(back_populates="publish_jobs")

