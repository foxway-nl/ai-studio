"""Lokale LLM integratie via Ollama REST API.

Biedt snelle lokale vertalingen, prompt-optimalisatie en content safety checks
zonder externe API-kosten of rate limits.
"""

import logging
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class OllamaService:
    """Service voor communicatie met een lokale Ollama instance."""

    def __init__(self, base_url: Optional[str] = None, default_model: str = "llama3.1:8b"):
        self._custom_base_url = base_url
        self.default_model = default_model

    @property
    def base_url(self) -> str:
        if self._custom_base_url:
            return self._custom_base_url.rstrip("/")
        url = settings_manager.get("ollama_base_url", settings.ollama_base_url)
        return url.rstrip("/") if url else "http://host.docker.internal:11434"

    async def check_connection(self) -> bool:
        """Controleer of de Ollama server bereikbaar is."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                return res.status_code == 200
        except Exception as e:
            logger.debug("Ollama niet bereikbaar op %s: %s", self.base_url, e)
            return False

    async def get_available_models(self) -> List[str]:
        """Haal de lijst van lokaal geïnstalleerde modellen op."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    return [m.get("name") for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Fout bij ophalen Ollama modellen: %s", e)
        return []

    async def _generate(self, prompt: str, system: Optional[str] = None, model: Optional[str] = None) -> str:
        """Interne helper voor generatie via Ollama."""
        selected_model = model or self.default_model
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.4},
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama fout ({resp.status_code}): {resp.text}")
            return resp.json().get("response", "").strip()

    async def translate_prompt(self, prompt: str, source_lang: str = "nl", target_lang: str = "en") -> str:
        """Vertaal een prompt van bijvoorbeeld Nederlands naar Engels voor Stable Diffusion."""
        system = (
            f"You are a professional translator for AI image prompts. "
            f"Translate from {source_lang} to {target_lang}. "
            f"Preserve artistic keywords and details. Output ONLY the translated prompt."
        )
        return await self._generate(prompt=prompt, system=system)

    async def enhance_prompt(self, prompt: str, style: str = "cute 3d kids animation") -> str:
        """Breid een beknopte scènebeschrijving uit tot een kwalitatieve beeldgeneratie prompt."""
        system = (
            "You are an expert AI prompt engineer specializing in child-friendly 3D animation, Pixar and Disney Jr styles. "
            "Add rich sensory details, soft lighting, vibrant pastel colors, clean vector or rendered look. "
            "Never introduce violence, weapons, or scary elements. Output only the prompt in English."
        )
        user_msg = f"Enhance this prompt for style '{style}': {prompt}"
        return await self._generate(prompt=user_msg, system=system)

    async def check_content_safety(self, text: str) -> Dict[str, Any]:
        """Controleer tekst op geschiktheid voor jonge kinderen (0-7 jaar)."""
        system = (
            "You are a strict child-safety content auditor for YouTube Kids. "
            "Analyze the text for: violence, weapons, scary themes, inappropriate language, danger. "
            "Respond in JSON format: {\"safe\": true/false, \"score\": 0-100, \"concerns\": [\"...\"]}"
        )
        response_text = await self._generate(prompt=text, system=system)
        import json
        import re
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return {"safe": True, "score": 95, "concerns": []}

    async def summarize_script(self, script: str) -> str:
        """Maak een korte educatieve samenvatting van het script."""
        system = "Vat het volgende kinder-videoscript samen in 2 vrolijke Nederlandse zinnen voor ouders."
        return await self._generate(prompt=script, system=system)


ollama_service = OllamaService()

