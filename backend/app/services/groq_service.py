"""Groq Free Tier Cloud integratie voor ultra-snelle tekst & Whisper transcriptie.

Ondersteunt:
- Llama 3.3 70B, Qwen QwQ 32B, Gemma 2 9B voor script, ideegeneratie en prompts
- Whisper Large v3 Turbo voor cloud-based realtime woord-level timestamps
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class GroqService:
    """Service voor communicatie met de Groq Cloud API."""

    def __init__(self):
        self.base_url = "https://api.groq.com/openai/v1"

    def get_api_key(self) -> str:
        """Haal de geconfigureerde Groq API-sleutel op."""
        raw = settings_manager.get("groq_api_key", settings.groq_api_key) or ""
        return raw.strip().strip('"').strip("'")

    def _headers(self, api_key: Optional[str] = None) -> Dict[str, str]:
        key = api_key or self.get_api_key()
        return {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }

    async def check_connection(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Controleer of de Groq API-sleutel geldig is en haal beschikbare modellen op."""
        key = api_key or self.get_api_key()
        if not key or settings_manager.is_masked_value(key):
            return {
                "connected": False,
                "error": "Groq API-sleutel ontbreekt. Voeg je gratis sleutel van console.groq.com/keys toe.",
                "models": [],
            }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(
                    f"{self.base_url}/models",
                    headers={"Authorization": f"Bearer {key}"},
                )
                if res.status_code == 200:
                    data = res.json()
                    all_ids = [m["id"] for m in data.get("data", [])]
                    # Filter op chat & text modellen
                    chat_models = [
                        m
                        for m in all_ids
                        if not m.startswith("whisper") and not "guard" in m
                    ]
                    # Sorteer met Llama-3.3 en Qwen bovenaan
                    prio = ["llama-3.3-70b-versatile", "qwen-qwq-32b", "gemma2-9b-it", "llama-3.1-8b-instant"]
                    ordered = [m for m in prio if m in chat_models] + [
                        m for m in chat_models if m not in prio
                    ]
                    return {
                        "connected": True,
                        "models": ordered,
                        "whisper_models": [m for m in all_ids if "whisper" in m],
                    }
                return {
                    "connected": False,
                    "error": f"Groq fout {res.status_code}: {res.text}",
                    "models": [],
                }
        except Exception as e:
            logger.warning("Fout bij verbinden met Groq: %s", e)
            return {"connected": False, "error": str(e), "models": []}

    async def list_models(self) -> List[str]:
        """Haal lijst op van gratis Groq tekstmodellen."""
        res = await self.check_connection()
        return res.get("models") or [
            "llama-3.3-70b-versatile",
            "qwen-qwq-32b",
            "gemma2-9b-it",
            "llama-3.1-8b-instant",
        ]

    async def generate_text(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
        temperature: float = 0.7,
    ) -> str:
        """Genereert tekst via Groq Chat Completions."""
        key = self.get_api_key()
        if not key:
            raise RuntimeError("Groq API-sleutel is niet ingesteld in de instellingen.")

        selected_model = (
            model
            or settings_manager.get("task_script_model")
            or "llama-3.3-70b-versatile"
        )
        messages: List[Dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": selected_model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(key),
                json=payload,
            )
            if resp.status_code != 200:
                raise RuntimeError(f"Groq API fout ({resp.status_code}): {resp.text}")
            data = resp.json()
            return data["choices"][0]["message"]["content"].strip()

    async def generate_ideas(self, target_audience: str = "kids", count: int = 5) -> List[str]:
        """Genereert 5 creatieve virale video-ideeën voor educatieve YouTube content."""
        system = (
            "Je bent een virale YouTube Kids content strateeg. "
            "Bedenk pakkende, educatieve en vrolijke onderwerpen voor peuters en kleuters (0-7 jaar). "
            "Geef uitsluitend een JSON object terug in het formaat: {\"ideas\": [\"Idee 1\", \"Idee 2\", ...]}"
        )
        prompt = f"Bedenk {count} unieke en virale video concepten voor de doelgroep '{target_audience}'."
        raw = await self.generate_text(prompt=prompt, system=system, json_mode=True, temperature=0.85)
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict) and "ideas" in parsed:
                return [str(x) for x in parsed["ideas"]][:count]
            if isinstance(parsed, list):
                return [str(x) for x in parsed][:count]
        except Exception:
            pass
        return [line.strip("- *12345. ") for line in raw.split("\n") if len(line.strip()) > 5][:count]

    async def generate_script(
        self,
        topic: str,
        target_audience: str = "kids",
        characters: Optional[List[Dict[str, Any]]] = None,
        scene_count: int = 5,
    ) -> Dict[str, Any]:
        """Genereert een compleet gestructureerd script inclusief scène-prompts."""
        chars_desc = ""
        if characters:
            chars_desc = "Beschikbare karakters: " + ", ".join(
                [f"{c.get('name')} ({c.get('description', '')})" for c in characters]
            )

        system = (
            "Je bent een ervaren kinderboekenschrijver en YouTube animatie-regisseur. "
            "Schrijf een vrolijk, leerzaam en meeslepend script in het Nederlands. "
            "Houd zinnen kort, energiek en begrijpelijk voor jonge kinderen. "
            "Elke scène moet een gesproken tekst (narration), een spreker, een beeld-prompt (in het Engels voor AI-beeldgeneratie) "
            "en een bewegingsopdracht (motion_prompt in het Engels) bevatten. "
            "Retourneer ALLEEN een geldig JSON object met de structuur: "
            "{\"title\": \"...\", \"scenes\": [{\"order\": 1, \"title\": \"...\", \"speaker\": \"...\", \"narration\": \"...\", \"visual_prompt\": \"...\", \"motion_prompt\": \"...\", \"duration_seconds\": 8}]}"
        )
        prompt = f"Onderwerp: {topic}\nDoelgroep: {target_audience}\nAantal scènes: {scene_count}\n{chars_desc}"
        raw = await self.generate_text(prompt=prompt, system=system, json_mode=True)
        return json.loads(raw)

    async def get_word_timestamps(self, audio_path: str) -> List[Dict[str, Any]]:
        """Haalt cloud-based woord-level timestamps op via Groq Whisper Large v3 Turbo."""
        key = self.get_api_key()
        if not key:
            raise RuntimeError("Groq API-sleutel ontbreekt voor Whisper transcriptie.")

        p = Path(audio_path)
        if not p.exists() or p.stat().st_size == 0:
            return []

        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {key}"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            with open(str(p), "rb") as f:
                files = {"file": (p.name, f, "audio/mpeg")}
                data = {
                    "model": "whisper-large-v3-turbo",
                    "response_format": "verbose_json",
                    "timestamp_granularities[]": ["word", "segment"],
                    "language": "nl",
                }
                resp = await client.post(url, headers=headers, data=data, files=files)
                if resp.status_code != 200:
                    raise RuntimeError(f"Groq Whisper fout ({resp.status_code}): {resp.text}")
                result = resp.json()

        words = result.get("words", [])
        return [
            {
                "word": w.get("word", "").strip(),
                "start": round(float(w.get("start", 0.0)), 3),
                "end": round(float(w.get("end", 0.0)), 3),
            }
            for w in words
            if w.get("word")
        ]


groq_service = GroqService()

