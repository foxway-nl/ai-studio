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
    voice_id: str = "nl-NL-FennaNeural"
    voice_provider: str = "edge_tts"
    voice_pitch: str = "+15Hz"
    voice_rate: str = "+0%"
    style_prompt: str = ""
    visual_dna_prompt: str = ""
    color_palette: str = ""


class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    personality: Optional[str] = None
    voice_id: Optional[str] = None
    voice_provider: Optional[str] = None
    voice_pitch: Optional[str] = None
    voice_rate: Optional[str] = None
    style_prompt: Optional[str] = None
    visual_dna_prompt: Optional[str] = None
    color_palette: Optional[str] = None


class ExpressionResponse(BaseModel):
    id: str
    name: str
    image_path: str
    image_url: Optional[str] = None
    mouth_open_path: Optional[str]
    mouth_open_url: Optional[str] = None
    mouth_closed_path: Optional[str]
    mouth_closed_url: Optional[str] = None
    created_at: datetime


class CharacterResponse(BaseModel):
    id: str
    project_id: str
    name: str
    description: str
    personality: str
    voice_id: str
    voice_provider: str
    voice_pitch: str = "+15Hz"
    voice_rate: str = "+0%"
    sprite_base_path: Optional[str]
    sprite_url: Optional[str] = None
    style_prompt: str
    visual_dna_prompt: str = ""
    color_palette: str
    reference_images: list[str] = []
    reference_image_urls: list[str] = []
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
    target_audience: str = "kids"  # kids | general
    made_for_kids: bool = True


class EpisodeUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=300)
    description: Optional[str] = None
    episode_number: Optional[int] = Field(default=None, ge=1)
    target_duration_seconds: Optional[int] = Field(default=None, ge=60, le=1800)
    target_duration: Optional[int] = Field(default=None, ge=60, le=1800)
    script_raw: Optional[str] = None
    script_final: Optional[str] = None
    seo_title: Optional[str] = None
    seo_description: Optional[str] = None
    seo_tags: Optional[str] = None
    thumbnail_prompt: Optional[str] = None
    bg_music_path: Optional[str] = None
    target_audience: Optional[str] = None
    made_for_kids: Optional[bool] = None
    status: Optional[str] = None


class EpisodeResponse(BaseModel):
    id: str
    project_id: str
    title: str
    description: str
    episode_number: int
    target_duration_seconds: int
    target_duration: int = 720
    script_raw: str
    script_final: str
    seo_title: str
    seo_description: str
    seo_tags: str
    thumbnail_prompt: str
    thumbnail_path: Optional[str]
    target_audience: str = "kids"
    made_for_kids: bool = True
    bg_music_path: str = ""
    status: str
    scene_count: int = 0
    render_url: Optional[str] = None
    youtube_url: Optional[str] = None
    youtube_video_id: str = ""
    guardrail_warnings: list[str] = []
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
    chapter_type: str = "chapter"
    speaker: str = ""
    active_speaker: str = "verteller"
    narration_text: Optional[str] = None
    narration: Optional[str] = None
    phonetic_text: str = ""
    visual_prompt: str = ""
    background_prompt: str = ""
    image_prompt: str = ""
    motion_prompt: str = ""
    video_clip_path: Optional[str] = None
    video_clip_url: Optional[str] = None
    animation_engine: str = "veo"
    character_ids: Any = ""
    characters_in_scene: Any = None
    character_positions: str = ""
    use_2d_sprite: bool = False
    sprite_config_json: str = ""
    animation_type: str = "ken_burns"
    transition_type: str = "crossfade"
    sfx_track: str = ""
    duration_seconds: Optional[float] = None
    duration: Optional[float] = None
    pause_after_sec: Optional[float] = 0.4


class SceneUpdate(BaseModel):
    scene_number: Optional[int] = None
    order: Optional[int] = None
    title: Optional[str] = None
    chapter_type: Optional[str] = None
    speaker: Optional[str] = None
    active_speaker: Optional[str] = None
    narration_text: Optional[str] = None
    narration: Optional[str] = None
    phonetic_text: Optional[str] = None
    visual_prompt: Optional[str] = None
    background_prompt: Optional[str] = None
    image_prompt: Optional[str] = None
    motion_prompt: Optional[str] = None
    video_clip_path: Optional[str] = None
    animation_engine: Optional[str] = None
    character_ids: Any = None
    characters_in_scene: Any = None
    character_positions: Optional[str] = None
    use_2d_sprite: Optional[bool] = None
    sprite_config_json: Optional[str] = None
    animation_type: Optional[str] = None
    transition_type: Optional[str] = None
    sfx_track: Optional[str] = None
    duration_seconds: Optional[float] = None
    duration: Optional[float] = None
    pause_after_sec: Optional[float] = None
    start_time: Optional[float] = None
    background_image_path: Optional[str] = None
    composite_image_path: Optional[str] = None
    audio_path: Optional[str] = None
    status: Optional[str] = None


class SceneHistoryItem(BaseModel):
    path: str
    url: Optional[str] = None
    prompt: str = ""
    created_at: str = ""


class GuardrailIssue(BaseModel):
    level: str = "warning"  # warning | error
    message: str
    scene_id: Optional[str] = None
    scene_number: Optional[int] = None


class EpisodeGuardrailsResponse(BaseModel):
    passed: bool = True
    safety_score: int = 100
    total_duration_seconds: float = 0.0
    scene_count: int = 0
    issues: list[GuardrailIssue] = []


class SceneResponse(BaseModel):
    id: str
    episode_id: str
    scene_number: int
    order: int = 1
    title: str
    chapter_type: str = "chapter"
    speaker: str = ""
    active_speaker: str = "verteller"
    narration_text: str = ""
    narration: str = ""
    phonetic_text: str = ""
    visual_prompt: str = ""
    background_prompt: str = ""
    image_prompt: str = ""
    motion_prompt: str = ""
    video_clip_path: Optional[str] = None
    video_clip_url: Optional[str] = None
    animation_engine: str = "veo"
    character_ids: Any = ""
    characters_in_scene: Any = []
    character_positions: str = ""
    use_2d_sprite: bool = False
    sprite_config_json: str = ""
    animation_type: str = "ken_burns"
    transition_type: str = "crossfade"
    sfx_track: str = ""
    duration_seconds: float = 8.0
    duration: float = 8.0
    pause_after_sec: float = 0.4
    background_image_path: Optional[str] = None
    composite_image_path: Optional[str] = None
    image_url: Optional[str] = None
    image_history: list[SceneHistoryItem] = []
    audio_path: Optional[str] = None
    audio_url: Optional[str] = None
    word_timestamps: list[dict] = []
    start_time: float = 0.0
    status: str = "draft"
    guardrail_warnings: list[str] = []
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


class VoiceTestRequest(BaseModel):
    voice_id: str = "nl-NL-FennaNeural"
    voice_provider: str = "edge_tts"
    text: str = "Hoi allemaal! Vandaag gaan we samen op avontuur, doen jullie mee?"
    pitch: str = "+15Hz"
    rate: str = "+0%"


class VoiceTestResponse(BaseModel):
    audio_url: str
    duration_seconds: float
    voice_id: str
    message: str = "Audio succesvol gegenereerd"


class GeminiTestRequest(BaseModel):
    api_key: Optional[str] = None


class GeminiTestResponse(BaseModel):
    valid: bool
    status_code: int
    models: list[str] = []
    text_models: list[str] = []
    image_models: list[str] = []
    message: str = ""
    error: Optional[str] = None


class YouTubeChannelResponse(BaseModel):
    connected: bool = False
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    custom_url: Optional[str] = None
    avatar_url: Optional[str] = None
    subscriber_count: Optional[str] = None
    video_count: Optional[str] = None


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


# ─────────────────────────────────────────────────────────────
# Video Animatie (Image-to-Video: Google Veo, Wan 2.1, Flow)
# ─────────────────────────────────────────────────────────────


class AnimateSceneRequest(BaseModel):
    animation_engine: str = "veo"  # veo | wan | ken_burns
    motion_prompt: Optional[str] = None


class AnimateSceneResponse(BaseModel):
    scene_id: str
    video_clip_url: str
    video_clip_path: str
    duration: float
    animation_engine: str
    message: str


class ExportFlowResponse(BaseModel):
    zip_url: str
    zip_path: str
    manifest_url: Optional[str] = None
    scene_count: int
    message: str


