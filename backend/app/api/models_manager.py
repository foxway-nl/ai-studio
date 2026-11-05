"""AI Model Beheercentrum API Router.

Biedt endpoints voor:
1. Lokale Ollama Model Manager (bekijken, verwijderen, installeren met live SSE streaming)
2. Groq Cloud Free Tier integratie (modellen ophalen, sleutel testen, transcriptie)
3. Hugging Face Free Tier & ZeroGPU integratie (token testen, space configuratie)
4. Centrale Taak-Router configuratie en virale idee-generatie
"""

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.settings_manager import SettingsManager, settings_manager
from app.services.ai_router import ai_router
from app.services.groq_service import groq_service
from app.services.huggingface_service import huggingface_service
from app.services.ollama_service import ollama_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/models", tags=["AI Model Management"])


class PullModelRequest(BaseModel):
    name: str


class TestKeyRequest(BaseModel):
    api_key: Optional[str] = None
    token: Optional[str] = None


class RouterConfigUpdate(BaseModel):
    task_script_provider: Optional[str] = None
    task_script_model: Optional[str] = None
    task_prompt_provider: Optional[str] = None
    task_prompt_model: Optional[str] = None
    task_tts_provider: Optional[str] = None
    task_tts_voice: Optional[str] = None
    task_whisper_provider: Optional[str] = None
    task_image_provider: Optional[str] = None
    task_image_model: Optional[str] = None
    task_video_provider: Optional[str] = None
    task_video_model: Optional[str] = None


class GenerateIdeasRequest(BaseModel):
    target_audience: Optional[str] = "kids"
    count: Optional[int] = 5


# ─────────────────────────────────────────────────────────────
# 1. Lokale Ollama Model Manager Endpoints
# ─────────────────────────────────────────────────────────────


@router.get("/ollama/installed")
async def get_ollama_installed_models():
    """Haal alle lokaal geïnstalleerde Ollama modellen op met GB-grootte en familie."""
    connected = await ollama_service.check_connection()
    if not connected:
        return {
            "connected": False,
            "models": [],
            "message": "Ollama server is momenteel niet bereikbaar op " + ollama_service.base_url,
        }

    models = await ollama_service.list_installed_models()
    return {
        "connected": True,
        "models": models,
        "count": len(models),
    }


@router.delete("/ollama/{model_name:path}")
async def delete_ollama_model(model_name: str):
    """Verwijder een lokaal Ollama model om schijfruimte vrij te maken."""
    success = await ollama_service.delete_model(model_name)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Kon model '{model_name}' niet verwijderen uit Ollama.",
        )
    return {"status": "success", "message": f"Model '{model_name}' succesvol verwijderd."}


@router.post("/ollama/pull")
async def pull_ollama_model(payload: PullModelRequest):
    """Download een nieuw model met een live Server-Sent Events (SSE) voortgangsbalk."""
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="Modelnaam mag niet leeg zijn.")

    async def event_generator():
        try:
            async for progress in ollama_service.pull_model_stream(name):
                yield f"data: {json.dumps(progress)}\n\n"
        except Exception as e:
            err = {"status": f"Fout: {e}", "completed": 0, "total": 0, "percent": 0.0, "error": True}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ─────────────────────────────────────────────────────────────
# 2. Groq Cloud Free Tier Endpoints
# ─────────────────────────────────────────────────────────────


@router.get("/groq")
async def get_groq_models():
    """Haal de actuele lijst van gratis Groq modellen op."""
    info = await groq_service.check_connection()
    return info


@router.post("/test-groq")
async def test_groq_key(payload: Optional[TestKeyRequest] = None):
    """Valideer een Groq API-sleutel en sla hem op indien geldig."""
    raw_key = payload.api_key.strip() if payload and payload.api_key else None
    if raw_key and SettingsManager.is_masked_value(raw_key):
        raw_key = None  # Gebruik reeds opgeslagen sleutel

    info = await groq_service.check_connection(api_key=raw_key)
    if info.get("connected") and raw_key:
        settings_manager.set("groq_api_key", raw_key, "Groq Cloud API sleutel")

    return info


# ─────────────────────────────────────────────────────────────
# 3. Hugging Face Free Tier & ZeroGPU Endpoints
# ─────────────────────────────────────────────────────────────


@router.post("/test-hf")
async def test_hf_token(payload: Optional[TestKeyRequest] = None):
    """Valideer een Hugging Face Access Token en sla hem op indien geldig."""
    raw_tok = payload.token.strip() if payload and payload.token else None
    if raw_tok and SettingsManager.is_masked_value(raw_tok):
        raw_tok = None

    info = await huggingface_service.check_connection(token=raw_tok)
    if info.get("connected") and raw_tok:
        settings_manager.set("hf_token", raw_tok, "Hugging Face Access Token")

    return info


# ─────────────────────────────────────────────────────────────
# 4. Taak-Router & Virale Ideeën Endpoints
# ─────────────────────────────────────────────────────────────


@router.get("/router/config")
async def get_task_router_config():
    """Haal de geconfigureerde taakverdeling op."""
    return ai_router.get_routing_config()


@router.put("/router/config")
async def update_task_router_config(payload: RouterConfigUpdate):
    """Werk de taakverdeling bij."""
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        if v is not None:
            settings_manager.set(k, str(v).strip())
    return ai_router.get_routing_config()


@router.post("/episodes/{episode_id}/generate-ideas")
async def generate_viral_ideas(episode_id: str, payload: Optional[GenerateIdeasRequest] = None):
    """Genereert 5 virale YouTube ideeën via de geconfigureerde Script-provider."""
    audience = payload.target_audience if payload and payload.target_audience else "kids"
    count = payload.count if payload and payload.count else 5
    ideas = await ai_router.generate_ideas(target_audience=audience, count=count)
    return {"episode_id": episode_id, "ideas": ideas}

