"""Hugging Face Free Tier & ZeroGPU integratie voor beeld- en video-animatie.

Ondersteunt:
- FLUX.1-schnell via Hugging Face Serverless Inference API (gratis start-frames & karakters)
- Echte Image-to-Video via publieke ZeroGPU Spaces (Wan 2.1 / LTX-Video) via gradio_client
"""

import asyncio
import io
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from PIL import Image

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class HuggingFaceService:
    """Service voor Hugging Face Free Tier Image & Video generatie."""

    def __init__(self):
        self.default_image_model = "black-forest-labs/FLUX.1-schnell"
        self.default_video_space = "multimodalart/Wan2.1-Fast"

    def get_token(self) -> str:
        """Haal het Hugging Face Access Token op."""
        raw = settings_manager.get("hf_token", settings.hf_token) or ""
        return raw.strip().strip('"').strip("'")

    def get_video_space(self) -> str:
        """Haal de geconfigureerde ZeroGPU Space ID op."""
        raw = settings_manager.get("hf_video_space_id", settings.hf_video_space_id) or self.default_video_space
        return raw.strip()

    async def check_connection(self, token: Optional[str] = None) -> Dict[str, Any]:
        """Controleer of het Hugging Face token geldig is."""
        tok = token or self.get_token()
        if not tok or settings_manager.is_masked_value(tok):
            return {
                "connected": False,
                "error": "Hugging Face Access Token ontbreekt. Maak een gratis token aan op huggingface.co/settings/tokens.",
                "user": None,
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    "https://huggingface.co/api/whoami-v2",
                    headers={"Authorization": f"Bearer {tok}"},
                )
                if res.status_code == 200:
                    data = res.json()
                    name = data.get("name") or data.get("fullname") or "Hugging Face Gebruiker"
                    return {
                        "connected": True,
                        "user": name,
                        "type": data.get("type", "user"),
                        "can_pay": data.get("canPay", False),
                    }
                return {
                    "connected": False,
                    "error": f"Hugging Face fout {res.status_code}: {res.text}",
                    "user": None,
                }
        except Exception as e:
            logger.warning("Fout bij verbinden met Hugging Face: %s", e)
            return {"connected": False, "error": str(e), "user": None}

    async def generate_image(
        self,
        prompt: str,
        output_path: str,
        width: int = 1280,
        height: int = 720,
        model: Optional[str] = None,
    ) -> str:
        """Genereert een Start-Frame of karakterplaatje via Hugging Face FLUX.1-schnell."""
        tok = self.get_token()
        if not tok:
            raise RuntimeError("Hugging Face token ontbreekt in de instellingen.")

        selected_model = model or self.default_image_model
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Probeer eerst via huggingface_hub InferenceClient
        try:
            from huggingface_hub import InferenceClient

            def _sync_generate():
                client = InferenceClient(provider="hf-inference", token=tok)
                # Genereer afbeelding met FLUX.1-schnell
                img = client.text_to_image(prompt=prompt, model=selected_model)
                img = img.resize((width, height), Image.Resampling.LANCZOS)
                img.save(output_path, "PNG")
                return output_path

            await asyncio.to_thread(_sync_generate)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                return output_path
        except Exception as e:
            logger.warning("InferenceClient faalde (%s), probeer directe HTTP API call...", e)

        # Fallback naar directe HTTP Inference API
        url = f"https://api-inference.huggingface.co/models/{selected_model}"
        headers = {
            "Authorization": f"Bearer {tok}",
            "Content-Type": "application/json",
        }
        payload = {
            "inputs": prompt,
            "parameters": {"width": width, "height": height},
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Hugging Face Inference API fout ({resp.status_code}): {resp.text}"
                )
            img = Image.open(io.BytesIO(resp.content))
            img = img.resize((width, height), Image.Resampling.LANCZOS)
            img.save(output_path, "PNG")

        if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
            raise RuntimeError("Hugging Face heeft geen geldige afbeelding gegenereerd.")
        return output_path

    async def generate_video_zerogpu(
        self,
        image_path: str,
        motion_prompt: str,
        output_path: str,
        space_id: Optional[str] = None,
    ) -> str:
        """Genereert echte Image-to-Video via een publieke Hugging Face ZeroGPU Space."""
        tok = self.get_token()
        target_space = space_id or self.get_video_space()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if not os.path.exists(image_path) or os.path.getsize(image_path) < 1000:
            raise RuntimeError(f"Start-Frame bestand niet gevonden: {image_path}")

        try:
            from gradio_client import Client, handle_file

            def _call_gradio():
                # Initialiseer client met optioneel HF token voor voorrang in ZeroGPU wachtrij
                client = Client(target_space, hf_token=tok if tok else None)

                # Zoek geschikt endpoint voor image-to-video
                # De meeste Wan 2.1 / LTX spaces accepteren (image, prompt)
                result = client.predict(
                    image=handle_file(image_path),
                    prompt=motion_prompt,
                    api_name="/predict",
                )
                return result

            result_file = await asyncio.to_thread(_call_gradio)
            if isinstance(result_file, (list, tuple)) and len(result_file) > 0:
                result_file = result_file[0]
            if isinstance(result_file, dict) and "video" in result_file:
                result_file = result_file["video"]

            result_str = str(result_file)
            if os.path.exists(result_str) and os.path.getsize(result_str) > 5000:
                shutil.copy2(result_str, output_path)
                return output_path
            raise RuntimeError(f"Gradio Space leverde ongeldig resultaat: {result_file}")

        except Exception as e:
            logger.error("Hugging Face ZeroGPU video generatie faalde op Space '%s': %s", target_space, e)
            raise RuntimeError(
                f"Hugging Face ZeroGPU ({target_space}) fout: {e}. "
                "Schakel over naar de ingebouwde Lokale 60fps 2.5D Animator of Google Veo als de ZeroGPU wachtrij vol is."
            )


huggingface_service = HuggingFaceService()

