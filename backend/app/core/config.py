"""Applicatie-configuratie via omgevingsvariabelen en Pydantic Settings."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Centrale configuratie, geladen uit omgevingsvariabelen of .env bestand."""

    # Paden
    data_dir: str = os.getenv("DATA_DIR", "/data")
    database_url: str = os.getenv("DATABASE_URL", "")

    @property
    def resolved_database_url(self) -> str:
        """Database-URL; leidt lokaal een SQLite-pad af uit DATA_DIR."""
        if self.database_url:
            return self.database_url
        return f"sqlite:///{Path(self.data_dir).expanduser().resolve() / 'ai_studio.db'}"

    # App
    app_secret_key: str = "change-me-to-a-random-string"
    log_level: str = "INFO"

    # Google Gemini
    gemini_api_key: str = ""

    # Groq Cloud Free Tier
    groq_api_key: str = ""

    # Hugging Face Free Tier & ZeroGPU
    hf_token: str = ""
    hf_video_space_id: str = "multimodalart/Wan2.1-Fast"

    # Taak-Router configuratie
    task_script_provider: str = "gemini"
    task_script_model: str = "gemini-2.5-flash"
    task_prompt_provider: str = "gemini"
    task_prompt_model: str = "gemini-2.5-flash"
    task_tts_provider: str = "edge_tts"
    task_tts_voice: str = "nl-NL-FennaNeural"
    task_whisper_provider: str = "groq_whisper"
    task_image_provider: str = "gemini_imagen"
    task_image_model: str = "imagen-3.0-generate-002"
    task_video_provider: str = "local_2_5d"
    task_video_model: str = "veo-2.0-generate-001"

    # Ollama
    ollama_base_url: str = "http://host.docker.internal:11434"

    # Stable Diffusion WebUI Forge
    sd_webui_base_url: str = "http://host.docker.internal:7860"

    # Google Cloud TTS
    google_tts_api_key: str = ""

    # YouTube
    youtube_client_id: str = ""
    youtube_client_secret: str = ""

    # Wan 2.1 / Open-Source Image-to-Video
    wan_api_url: str = "http://host.docker.internal:8188"
    wan_api_key: str = ""

    # Piper TTS
    piper_model_path: str = "/data/piper-models"

    # Kokoro TTS
    kokoro_base_url: str = "http://host.docker.internal:8080"

    @property
    def media_dir(self) -> Path:
        """Pad naar media-opslag (afbeeldingen, audio, renders)."""
        p = Path(self.data_dir) / "media"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def characters_dir(self) -> Path:
        p = Path(self.data_dir) / "media" / "characters"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def audio_dir(self) -> Path:
        p = Path(self.data_dir) / "media" / "audio"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def images_dir(self) -> Path:
        p = Path(self.data_dir) / "media" / "images"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def renders_dir(self) -> Path:
        p = Path(self.data_dir) / "media" / "renders"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def sprites_dir(self) -> Path:
        p = Path(self.data_dir) / "media" / "sprites"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def clips_dir(self) -> Path:
        """Pad naar geanimeerde videoclips (Google Veo, Wan 2.1, uploads)."""
        p = Path(self.data_dir) / "media" / "clips"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def exports_dir(self) -> Path:
        """Pad naar Google Flow bulk export zip bestanden."""
        p = Path(self.data_dir) / "media" / "exports"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def temp_dir(self) -> Path:
        p = Path(self.data_dir) / "temp"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def assets_dir(self) -> Path:
        """Vaste media-assets zoals intro/outro bumpers."""
        p = Path(self.data_dir) / "assets"
        p.mkdir(parents=True, exist_ok=True)
        return p

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = AppSettings()

