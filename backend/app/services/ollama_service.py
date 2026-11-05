"""Lokale LLM integratie via Ollama REST API.

Biedt:
- Bekijken van geïnstalleerde modellen met grootte in GB en familie
- Verwijderen van modellen via DELETE /api/delete
- Installeren (pullen) van nieuwe modellen met live streaming voortgang (0% - 100%)
- Genereren van scripts, virale ideeën en prompts zonder externe API kosten
"""

import json
import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class OllamaService:
    """Service voor communicatie met een lokale Ollama instance."""

    def __init__(self, base_url: Optional[str] = None, default_model: str = "qwen2.5:3b"):
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
        """Haal de lijst van lokaal geïnstalleerde modelnamen op."""
        models = await self.list_installed_models()
        return [m["name"] for m in models if "name" in m]

    async def list_installed_models(self) -> List[Dict[str, Any]]:
        """Haal gedetailleerde info van alle geïnstalleerde modellen op (naam, GB, familie)."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = []
                    for m in data.get("models", []):
                        size_bytes = m.get("size", 0)
                        size_gb = round(size_bytes / (1024**3), 2)
                        details = m.get("details", {})
                        models.append(
                            {
                                "name": m.get("name"),
                                "model": m.get("model", m.get("name")),
                                "size_bytes": size_bytes,
                                "size_gb": size_gb,
                                "family": details.get("family", "llm"),
                                "parameter_size": details.get("parameter_size", ""),
                                "quantization_level": details.get("quantization_level", ""),
                                "modified_at": m.get("modified_at", ""),
                            }
                        )
                    return models
        except Exception as e:
            logger.warning("Fout bij ophalen Ollama modellen: %s", e)
        return []

    async def delete_model(self, model_name: str) -> bool:
        """Verwijder een model uit Ollama om schijfruimte vrij te maken."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                # Ollama DELETE /api/delete accepteert JSON {"name": model_name}
                req = client.build_request("DELETE", f"{self.base_url}/api/delete", json={"name": model_name})
                res = await client.send(req)
                return res.status_code == 200
        except Exception as e:
            logger.error("Fout bij verwijderen Ollama model %s: %s", model_name, e)
            return False

    async def pull_model_stream(self, model_name: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Download een nieuw model van Ollama Library met live voortgang."""
        url = f"{self.base_url}/api/pull"
        payload = {"name": model_name, "stream": True}

        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield {
                        "status": f"Fout bij downloaden: HTTP {response.status_code}",
                        "completed": 0,
                        "total": 0,
                        "percent": 0.0,
                        "error": True,
                    }
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        status = data.get("status", "")
                        completed = data.get("completed", 0)
                        total = data.get("total", 0)
                        percent = round((completed / total) * 100, 1) if total > 0 else 0.0

                        yield {
                            "status": status,
                            "completed": completed,
                            "total": total,
                            "percent": percent,
                            "error": "error" in data,
                        }
                    except Exception:
                        pass

    async def _generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        json_mode: bool = False,
    ) -> str:
        """Interne helper voor generatie via Ollama."""
        selected_model = (
            model
            or settings_manager.get("task_script_model")
            or self.default_model
        )
        payload: Dict[str, Any] = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.6},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama fout ({resp.status_code}): {resp.text}")
            return resp.json().get("response", "").strip()

    async def generate_ideas(self, target_audience: str = "kids", count: int = 5) -> List[str]:
        """Bedenkt 5 educatieve video-ideeën met het lokale Ollama model."""
        system = (
            "Je bent een virale YouTube Kids content strateeg. "
            "Bedenk vrolijke, educatieve en boeiende onderwerpen voor jonge kinderen. "
            "Geef uitsluitend een JSON object terug: {\"ideas\": [\"Idee 1\", \"Idee 2\", ...]}"
        )
        prompt = f"Bedenk {count} unieke concepten voor doelgroep: {target_audience}."
        raw = await self._generate(prompt=prompt, system=system, json_mode=True)
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
        """Genereert een compleet gestructureerd script met het lokale Ollama model."""
        chars_desc = ""
        if characters:
            chars_desc = "Karakters: " + ", ".join(
                [f"{c.get('name')} ({c.get('description', '')})" for c in characters]
            )

        system = (
            "Schrijf een kindvriendelijk YouTube script in het Nederlands. "
            "Retourneer ALLEEN geldig JSON met: "
            "{\"title\": \"...\", \"scenes\": [{\"order\": 1, \"title\": \"...\", \"speaker\": \"...\", \"narration\": \"...\", \"visual_prompt\": \"...\", \"motion_prompt\": \"...\", \"duration_seconds\": 8}]}"
        )
        prompt = f"Onderwerp: {topic}\nDoelgroep: {target_audience}\nAantal scènes: {scene_count}\n{chars_desc}"
        raw = await self._generate(prompt=prompt, system=system, json_mode=True)
        return json.loads(raw)

    async def translate_prompt(self, prompt: str, source_lang: str = "nl", target_lang: str = "en") -> str:
        """Vertaal een prompt naar Engels voor AI beeldgeneratie."""
        system = (
            f"You are a professional translator for AI image prompts. "
            f"Translate from {source_lang} to {target_lang}. "
            f"Output ONLY the translated prompt."
        )
        return await self._generate(prompt=prompt, system=system)

    async def enhance_prompt(self, prompt: str, style: str = "cute 3d kids animation") -> str:
        """Breid een scènebeschrijving uit tot een hoogwaardige 3D beeldprompt."""
        system = (
            "You are an expert AI prompt engineer for child-friendly 3D Pixar animation. "
            "Output ONLY the enhanced prompt in English."
        )
        return await self._generate(prompt=f"Enhance for '{style}': {prompt}", system=system)


ollama_service = OllamaService()
