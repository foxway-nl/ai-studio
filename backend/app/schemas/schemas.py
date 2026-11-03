"""Strikte Pydantic v2 validatie-schema's voor alle API endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────
# Settings
# ─────────────────────────────────────────────────────────────


class SettingUpdate(BaseModel):
    key: str
    value: str
    description: str = ""


class SettingResponse(BaseModel):
    key: str
    value: str
    description: str = ""
    masked_value: Optional[str] = None


class ServiceStatus(BaseModel):
    name: str
    configured: bool = False
    connected: bool = False
    error: Optional[str] = None
    instructions_nl: str = ""


class SetupStatusResponse(BaseModel):
    services: list[ServiceStatus]
    all_configured: bool = False


# ─────────────────────────────────────────────────────────────
# Project
# ─────────────────────────────────────────────────────────────


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    target_age_min: int = Field(default=3, ge=0, le=12)
    target_age_max: int = Field(default=7, ge=0, le=12)
    language: str = "nl"
    channel_name: str = ""


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    target_age_min: Optional[int] = Field(default=None, ge=0, le=12)
    target_age_max: Optional[int] = Field(default=None, ge=0, le=12)
    language: Optional[str] = None
    channel_name: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    target_age_min: int
    target_age_max: int
    language: str
    channel_name: str
    thumbnail_path: Optional[str]
    episode_count: int = 0
    character_count: int = 0
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────
# Character
# ─────────────────────────────────────────────────────────────


class CharacterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = ""
    personality: str = ""
    voice_id: str = ""
    voice_provider: str = "piper"
    style_prompt: str = ""
    color_palette: str = ""


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    personality: Optional[str] = None
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    style_prompt: Optional[str] = None
    color_palette: Optional[str] = None


class ExpressionResponse(BaseModel):
    id: str
    name: str
    image_path: str
    mouth_open_path: Optional[str]
    mouth_closed_path: Optional[str]
    created_at: datetime


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    personality: str
    voice_id: str
    voice_provider: str
    sprite_base_path: Optional[str]
    style_prompt: str
    color_palette: str
    expressions: list[ExpressionResponse] = []
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────
# Episode
# ─────────────────────────────────────────────────────────────


class EpisodeCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    episode_number: int = Field(default=1, ge=1)
    target_duration_seconds: int = Field(default=720, ge=60, le=1800)


class EpisodeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    episode_number: Optional[int] = Field(default=None, ge=1)
    target_duration_seconds: Optional[int] = Field(default=None, ge=60, le=1800)
    script_raw: Optional[str] = None
    script_final: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_tags: Optional[str] = None
    thumbnail_prompt: Optional[str] = None
    status: Optional[str] = None


class EpisodeResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    episode_number: int
    target_duration_seconds: int
    script_raw: str
    script_final: str
    seo_title: str
    seo_description: str
    seo_tags: str
    thumbnail_prompt: str
    thumbnail_path: Optional[str]
    status: str
    scene_count: int = 0
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────
# Scene
# ─────────────────────────────────────────────────────────────


class SceneCreate(BaseModel):
    episode_id: Optional[str] = None
    scene_number: Optional[int] = None
    order: Optional[int] = None
    title: str = ""
    narration_text: Optional[str] = None
    narration: Optional[str] = None
    visual_prompt: str = ""
    background_prompt: str = ""
    character_ids: Any = ""
    character_positions: str = ""
    animation_type: str = "ken_burns"
    transition_type: str = "crossfade"
    duration_seconds: Optional[float] = None
    duration: Optional[float] = None


class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    order: Optional[int] = None
    title: Optional[str] = None
    narration_text: Optional[str] = None
    narration: Optional[str] = None
    visual_prompt: Optional[str] = None
    background_prompt: Optional[str] = None
    character_ids: Any = None
    character_positions: Optional[str] = None
    animation_type: Optional[str] = None
    transition_type: Optional[str] = None
    duration_seconds: Optional[float] = None
    duration: Optional[float] = None
    start_time: Optional[float] = None


class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    order: int = 1
    title: str
    narration_text: str = ""
    narration: str = ""
    visual_prompt: str = ""
    background_prompt: str = ""
    character_ids: Any = ""
    character_positions: str = ""
    animation_type: str = "ken_burns"
    transition_type: str = "crossfade"
    duration_seconds: float = 8.0
    duration: float = 8.0
    background_image_path: Optional[str] = None
    composite_image_path: Optional[str] = None
    image_url: Optional[str] = None
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    start_time: float = 0.0
    status: str = "draft"
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────
# AudioTrack
# ─────────────────────────────────────────────────────────────


class AudioTrackCreate(BaseModel):
    track_type: str = "narration"
    name: str = ""
    voice_id: str = ""
    voice_provider: str = "piper"
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    start_time: float = Field(default=0.0, ge=0.0)


class AudioTrackUpdate(BaseModel):
    name: Optional[str] = None
    volume: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    start_time: Optional[float] = Field(default=None, ge=0.0)


class AudioTrackResponse(BaseModel):
    id: str
    episode_id: str
    track_type: str
    name: str
    file_path: str
    duration_seconds: float
    volume: float
    start_time: float
    voice_id: str
    voice_provider: str
    word_timestamps: str
    status: str
    error_message: str
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# RenderJob
# ─────────────────────────────────────────────────────────────


class RenderJobCreate(BaseModel):
    resolution: str = "1920x1080"
    fps: int = Field(default=30, ge=24, le=60)


class RenderJobResponse(BaseModel):
    id: str
    episode_id: str
    status: str
    progress: float
    current_step: str
    output_path: Optional[str]
    resolution: str
    fps: int
    error_message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# PublishJob
# ─────────────────────────────────────────────────────────────


class PublishJobCreate(BaseModel):
    privacy_status: str = "private"
    made_for_kids: bool = True


class PublishJobResponse(BaseModel):
    id: str
    episode_id: str
    status: str
    progress: float
    youtube_video_id: Optional[str]
    youtube_url: Optional[str]
    privacy_status: str
    made_for_kids: bool
    error_message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Script generatie
# ─────────────────────────────────────────────────────────────


class ScriptGenerateRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=500)
    target_age_min: int = Field(default=3, ge=0, le=12)
    target_age_max: int = Field(default=7, ge=0, le=12)
    duration_minutes: int = Field(default=12, ge=5, le=20)
    language: str = "nl"
    style: str = "educatief en speels"
    characters: list[str] = []
    additional_instructions: str = ""


class ScriptGenerateResponse(BaseModel):
    script: str
    scenes: list[dict]
    seo_title: str
    seo_description: str
    seo_tags: list[str]
    thumbnail_prompt: str


# ─────────────────────────────────────────────────────────────
# Image generatie
# ─────────────────────────────────────────────────────────────


class ImageGenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=2000)
    negative_prompt: str = ""
    width: int = Field(default=1920, ge=256, le=4096)
    height: int = Field(default=1080, ge=256, le=4096)
    provider: str = "sdwebui"  # sdwebui | imagen
    style: str = "kids_illustration"


class ImageGenerateResponse(BaseModel):
    image_path: str
    provider: str
    seed: int = 0


# ─────────────────────────────────────────────────────────────
# TTS
# ─────────────────────────────────────────────────────────────


class TTSRequest(BaseModel):
    text: str = Field(min_length=1)
    voice_id: str = ""
    provider: str = "piper"  # piper | google | kokoro
    language: str = "nl"
    speed: float = Field(default=1.0, ge=0.5, le=2.0)


class TTSResponse(BaseModel):
    audio_path: str
    duration_seconds: float
    word_timestamps: list[dict]


# ─────────────────────────────────────────────────────────────
# Generiek
# ─────────────────────────────────────────────────────────────


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: float = 0.0
    current_step: str = ""
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "1.0.0"

