"""Centrale AI Taak-Router voor AI-Studio.

Biedt een flexibele dispatcher op basis van de in het AI Model Beheercentrum
gekozen providers voor:
1. Script & SEO (Groq Cloud, Google Gemini, of Lokaal Ollama)
2. Beeld- & Motion Prompts (Groq Cloud, Google Gemini, of Lokaal Ollama)
3. Stemmen TTS (Microsoft Edge-TTS of Google Gemini Audio)
4. Audio Timestamps (Groq Whisper Large v3 Turbo of Lokaal faster-whisper)
5. Start-Frames & Karakters (Hugging Face FLUX.1-schnell of Google Imagen 3)
6. Video-Animaties (Hugging Face ZeroGPU Wan 2.1 / LTX, Google Veo, of Lokale 60fps 2.5D FFmpeg)
"""

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.core.settings_manager import settings_manager
from app.services.audio_service import audio_service
from app.services.gemini_service import gemini_service
from app.services.groq_service import groq_service
from app.services.huggingface_service import huggingface_service
from app.services.ollama_service import ollama_service
from app.services.video_animation_service import video_animation_service

logger = logging.getLogger(__name__)


class AIRouterService:
    """Dynamische router die taken naar de gekozen AI-provider stuurt."""

    def get_routing_config(self) -> Dict[str, str]:
        """Haal de huidige taakverdeling op."""
        return {
            "task_script_provider": settings_manager.get("task_script_provider", settings.task_script_provider) or "gemini",
            "task_script_model": settings_manager.get("task_script_model", settings.task_script_model) or "gemini-2.5-flash",
            "task_prompt_provider": settings_manager.get("task_prompt_provider", settings.task_prompt_provider) or "gemini",
            "task_prompt_model": settings_manager.get("task_prompt_model", settings.task_prompt_model) or "gemini-2.5-flash",
            "task_tts_provider": settings_manager.get("task_tts_provider", settings.task_tts_provider) or "edge_tts",
            "task_tts_voice": settings_manager.get("task_tts_voice", settings.task_tts_voice) or "nl-NL-FennaNeural",
            "task_whisper_provider": settings_manager.get("task_whisper_provider", settings.task_whisper_provider) or "groq_whisper",
            "task_image_provider": settings_manager.get("task_image_provider", settings.task_image_provider) or "gemini_imagen",
            "task_image_model": settings_manager.get("task_image_model", settings.task_image_model) or "imagen-3.0-generate-002",
            "task_video_provider": settings_manager.get("task_video_provider", settings.task_video_provider) or "local_2_5d",
            "task_video_model": settings_manager.get("task_video_model", settings.task_video_model) or "veo-2.0-generate-001",
        }

    # ─────────────────────────────────────────────────────────────
    # 1. Ideeën & Script Generatie
    # ─────────────────────────────────────────────────────────────

    async def generate_ideas(self, target_audience: str = "kids", count: int = 5) -> List[str]:
        """Bedenk virale video-ideeën met de geselecteerde provider."""
        cfg = self.get_routing_config()
        provider = cfg["task_script_provider"]

        if provider == "groq" and groq_service.get_api_key():
            try:
                return await groq_service.generate_ideas(target_audience=target_audience, count=count)
            except Exception as e:
                logger.warning("Groq ideas generatie faalde (%s), val terug op Gemini.", e)

        if provider == "ollama" and await ollama_service.check_connection():
            try:
                return await ollama_service.generate_ideas(target_audience=target_audience, count=count)
            except Exception as e:
                logger.warning("Ollama ideas generatie faalde (%s), val terug op Gemini.", e)

        # Fallback naar Gemini
        prompt = (
            f"Bedenk {count} vrolijke, educatieve en virale video concepten voor YouTube Kids ({target_audience}). "
            "Geef uitsluitend een JSON array terug: [\"Idee 1\", \"Idee 2\", ...]"
        )
        try:
            raw = await gemini_service.generate_script(
                prompt=prompt,
                character_names=["Adam", "Nora"],
                scene_count=count,
            )
            if isinstance(raw, dict) and "scenes" in raw:
                return [s.get("title", f"Idee {i+1}") for i, s in enumerate(raw["scenes"][:count])]
        except Exception:
            pass

        return [
            "De Magische Kleurenboom in het Bos",
            "Adam en Nora Leren Tellen met Dieren",
            "Waarom Regen Plonst: Het Water Avontuur",
            "De Trein der Vormen en Cijfers",
            "Samen Delen en Fruit Proeven in de Tuin",
        ]

    async def generate_script(
        self,
        topic: str,
        target_audience: str = "kids",
        characters: Optional[List[Dict[str, Any]]] = None,
        scene_count: int = 5,
    ) -> Dict[str, Any]:
        """Genereert het volledige afleveringscript via de gekozen provider."""
        cfg = self.get_routing_config()
        provider = cfg["task_script_provider"]

        if provider == "groq" and groq_service.get_api_key():
            try:
                return await groq_service.generate_script(
                    topic=topic,
                    target_audience=target_audience,
                    characters=characters,
                    scene_count=scene_count,
                )
            except Exception as e:
                logger.warning("Groq script generatie faalde (%s), probeer Gemini.", e)

        if provider == "ollama" and await ollama_service.check_connection():
            try:
                return await ollama_service.generate_script(
                    topic=topic,
                    target_audience=target_audience,
                    characters=characters,
                    scene_count=scene_count,
                )
            except Exception as e:
                logger.warning("Ollama script generatie faalde (%s), probeer Gemini.", e)

        # Gemini
        char_names = [c.get("name", "Karakter") for c in (characters or [])]
        return await gemini_service.generate_script(
            prompt=topic,
            character_names=char_names,
            scene_count=scene_count,
            target_audience=target_audience,
        )

    # ─────────────────────────────────────────────────────────────
    # 2. Beeld- en Motion Prompts
    # ─────────────────────────────────────────────────────────────

    async def generate_motion_prompt(
        self,
        narration: str,
        visual_desc: str,
        characters_present: Optional[List[str]] = None,
    ) -> str:
        """Genereert een specifieke Engelse bewegingsopdracht voor de animatie-engine."""
        cfg = self.get_routing_config()
        provider = cfg["task_prompt_provider"]

        prompt = (
            f"Write a smooth, vivid 1-sentence English motion prompt for a 3D animated scene. "
            f"Narration: '{narration}'. Visual setting: '{visual_desc}'. "
            f"Characters present: {', '.join(characters_present or ['A friendly cartoon character'])}. "
            "Focus on cheerful walking, waving, pointing, jumping or laughing. Lively character animation."
        )

        if provider == "groq" and groq_service.get_api_key():
            try:
                return await groq_service.generate_text(
                    prompt=prompt,
                    system="You are a professional 3D character animator. Output ONLY the motion prompt.",
                )
            except Exception:
                pass

        return await gemini_service.generate_scene_motion_prompt(
            narration=narration,
            visual_desc=visual_desc,
            characters_present=characters_present,
        )

    # ─────────────────────────────────────────────────────────────
    # 3. Woord Timestamps (Lip-sync & Chapters)
    # ─────────────────────────────────────────────────────────────

    async def get_word_timestamps(self, audio_path: str) -> List[Dict[str, Any]]:
        """Haalt woord-level timestamps op via Groq Whisper of lokaal."""
        cfg = self.get_routing_config()
        provider = cfg["task_whisper_provider"]

        if provider == "groq_whisper" and groq_service.get_api_key():
            try:
                return await groq_service.get_word_timestamps(audio_path)
            except Exception as e:
                logger.warning("Groq Whisper faalde (%s), val terug op lokaal.", e)

        # Lokaal faster-whisper
        return await audio_service.get_word_timestamps(audio_path)

    # ─────────────────────────────────────────────────────────────
    # 4. Beeldgeneratie (Start-Frames & Karakters)
    # ─────────────────────────────────────────────────────────────

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        reference_images: Optional[List[str]] = None,
    ) -> str:
        """Genereert een start-frame of karakterafbeelding via HF FLUX.1 of Gemini Imagen."""
        cfg = self.get_routing_config()
        provider = cfg["task_image_provider"]

        # 1. Hugging Face FLUX.1-schnell (Gratis met token)
        if provider == "hf_flux" and huggingface_service.get_token():
            try:
                return await huggingface_service.generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    width=width,
                    height=height,
                )
            except Exception as e:
                logger.warning("Hugging Face FLUX generatie faalde (%s), probeer Gemini Imagen.", e)

        # 2. Google Gemini / Imagen 3
        try:
            return await gemini_service.generate_image(
                prompt=prompt,
                output_path=output_path,
                aspect_ratio="16:9",
                reference_images=reference_images,
            )
        except Exception as gemini_err:
            # Als Gemini faalt en HF token is beschikbaar, probeer HF alsnog
            if huggingface_service.get_token():
                logger.info("Gemini Imagen faalde (%s), probeer Hugging Face FLUX...", gemini_err)
                return await huggingface_service.generate_image(
                    prompt=prompt,
                    output_path=output_path,
                    width=width,
                    height=height,
                )
            raise gemini_err

    # ─────────────────────────────────────────────────────────────
    # 5. Video-Animatie
    # ─────────────────────────────────────────────────────────────

    async def generate_video_clip(
        self,
        image_path: str,
        output_path: str,
        motion_prompt: str = "",
        duration_seconds: float = 8.0,
        engine: Optional[str] = None,
    ) -> str:
        """Genereert een echte video-animatieclip via de gekozen engine."""
        cfg = self.get_routing_config()
        chosen_engine = engine or cfg["task_video_provider"]

        # 1. Hugging Face ZeroGPU (Wan 2.1 / LTX-Video)
        if chosen_engine in ("hf_zerogpu", "wan_zerogpu"):
            try:
                return await huggingface_service.generate_video_zerogpu(
                    image_path=image_path,
                    motion_prompt=motion_prompt,
                    output_path=output_path,
                )
            except Exception as e:
                logger.warning("ZeroGPU video generatie faalde (%s), val terug op lokale 60fps 2.5D animator.", e)

        # 2. Google Veo 2.0 API
        if chosen_engine in ("veo", "google_veo"):
            try:
                return await video_animation_service.generate_veo_video(
                    image_path=image_path,
                    output_path=output_path,
                    motion_prompt=motion_prompt,
                    duration_seconds=duration_seconds,
                )
            except Exception as e:
                logger.warning("Google Veo faalde (%s), val terug op lokale 60fps 2.5D animator.", e)

        # 3. Directe Lokale 60fps 2.5D Animator (FFmpeg)
        motion_type = "zoom_in"
        lower_p = motion_prompt.lower()
        if "pan left" in lower_p or "left" in lower_p:
            motion_type = "pan_left"
        elif "pan right" in lower_p or "right" in lower_p:
            motion_type = "pan_right"
        elif "zoom out" in lower_p or "out" in lower_p:
            motion_type = "zoom_out"

        return await video_animation_service.generate_local_2_5d_video(
            image_path=image_path,
            output_path=output_path,
            duration_seconds=duration_seconds,
            fps=60,
            motion_type=motion_type,
        )


ai_router = AIRouterService()

