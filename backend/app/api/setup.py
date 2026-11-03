"""Setup Centrum router – service status, connecties testen en instellingen beheren."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.settings_manager import settings_manager
from app.schemas.schemas import (
    ServiceStatus,
    SettingResponse,
    SettingUpdate,
    SetupStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["Setup"])

# Sleutels die gemaskeerd moeten worden in de UI
_SENSITIVE_KEYS = {
    "gemini_api_key",
    "google_tts_api_key",
    "youtube_client_secret",
    "app_secret_key",
}


def _mask_value(key: str, value: str) -> Optional[str]:
    """Maskeer gevoelige waarden voor weergave."""
    if key not in _SENSITIVE_KEYS or not value:
        return None
    if len(value) <= 8:
        return "****"
    return value[:4] + "****" + value[-4:]


async def _check_gemini() -> ServiceStatus:
    """Controleer Gemini API configuratie en verbinding."""
    api_key = settings_manager.get("gemini_api_key", settings.gemini_api_key)
    status = ServiceStatus(
        name="Gemini",
        instructions_nl=(
            "Stel je Gemini API-sleutel in via het Setup Centrum. "
            "Ga naar https://aistudio.google.com/apikey om een sleutel aan te maken."
        ),
    )
    if not api_key:
        return status
    status.configured = True
    try:
        from app.services.gemini_service import GeminiService

        service = GeminiService(api_key=api_key)
        status.connected = await service.test_connection()
        if not status.connected:
            status.error = "Gemini API-sleutel is ongeldig of de API is niet bereikbaar."
    except Exception as exc:
        status.error = str(exc)
    return status


async def _check_ollama() -> ServiceStatus:
    """Controleer Ollama verbinding."""
    base_url = settings_manager.get("ollama_base_url", settings.ollama_base_url)
    status = ServiceStatus(
        name="Ollama",
        instructions_nl=(
            "Installeer Ollama via https://ollama.ai en start de server. "
            "Standaard draait Ollama op http://localhost:11434."
        ),
    )
    if not base_url:
        return status
    status.configured = True
    try:
        from app.services.ollama_service import OllamaService

        service = OllamaService(base_url=base_url)
        connected = await service.check_connection()
        status.connected = connected
        if not connected:
            status.error = "Kan geen verbinding maken met Ollama"
    except Exception as exc:
        status.error = str(exc)
    return status


async def _check_sd_webui() -> ServiceStatus:
    """Controleer Stable Diffusion WebUI Forge verbinding."""
    base_url = settings_manager.get("sd_webui_base_url", settings.sd_webui_base_url)
    status = ServiceStatus(
        name="SD WebUI",
        instructions_nl=(
            "Installeer Stable Diffusion WebUI Forge en start met --api flag. "
            "Standaard draait het op http://localhost:7860. "
            "Zorg dat de API modus is ingeschakeld."
        ),
    )
    if not base_url:
        return status
    status.configured = True
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/sdapi/v1/options")
            status.connected = resp.status_code == 200
            if not status.connected:
                status.error = f"HTTP status {resp.status_code}"
    except Exception as exc:
        status.error = str(exc)
    return status


async def _check_piper() -> ServiceStatus:
    """Controleer Piper TTS beschikbaarheid."""
    model_path = settings_manager.get("piper_model_path", settings.piper_model_path)
    status = ServiceStatus(
        name="Piper TTS",
        instructions_nl=(
            "Installeer Piper TTS en download een Nederlands stemmodel. "
            "Configureer het pad naar de modellen in het Setup Centrum."
        ),
    )
    if not model_path:
        return status
    status.configured = True
    try:
        from pathlib import Path

        path = Path(model_path)
        if path.exists():
            status.connected = True
        else:
            status.error = f"Model pad bestaat niet: {model_path}"
    except Exception as exc:
        status.error = str(exc)
    return status


async def _check_kokoro() -> ServiceStatus:
    """Controleer Kokoro TTS verbinding."""
    base_url = settings_manager.get("kokoro_base_url", settings.kokoro_base_url)
    status = ServiceStatus(
        name="Kokoro TTS",
        instructions_nl=(
            "Start de Kokoro TTS server. "
            "Standaard draait het op http://localhost:8080."
        ),
    )
    if not base_url:
        return status
    status.configured = True
    try:
        import httpx

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{base_url}/health")
            status.connected = resp.status_code == 200
            if not status.connected:
                status.error = f"HTTP status {resp.status_code}"
    except Exception as exc:
        status.error = str(exc)
    return status


async def _check_youtube() -> ServiceStatus:
    """Controleer YouTube API configuratie."""
    client_id = settings_manager.get("youtube_client_id", settings.youtube_client_id)
    client_secret = settings_manager.get("youtube_client_secret", settings.youtube_client_secret)
    status = ServiceStatus(
        name="YouTube",
        instructions_nl=(
            "Maak een OAuth 2.0 client aan in de Google Cloud Console. "
            "Activeer de YouTube Data API v3 en stel de client-ID en secret in."
        ),
    )
    if not client_id or not client_secret:
        return status
    status.configured = True
    status.connected = True  # OAuth vereist user-interactie, dus we checken alleen de config
    return status


_SERVICE_CHECKERS = {
    "gemini": _check_gemini,
    "ollama": _check_ollama,
    "sd_webui": _check_sd_webui,
    "piper": _check_piper,
    "kokoro": _check_kokoro,
    "youtube": _check_youtube,
}


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status():
    """Controleer de status van alle services en geef instructies voor niet-geconfigureerde services."""
    services: list[ServiceStatus] = []
    for checker in _SERVICE_CHECKERS.values():
        try:
            svc_status = await checker()
            services.append(svc_status)
        except Exception as exc:
            logger.exception("Fout bij controleren service: %s", exc)

    all_configured = all(s.configured for s in services)
    return SetupStatusResponse(services=services, all_configured=all_configured)


@router.post("/test/{service_name}", response_model=ServiceStatus)
async def test_service(service_name: str):
    """Live-test de verbinding met een specifieke service."""
    checker = _SERVICE_CHECKERS.get(service_name)
    if checker is None:
        raise HTTPException(
            status_code=404,
            detail=f"Onbekende service: {service_name}. "
            f"Beschikbaar: {', '.join(_SERVICE_CHECKERS.keys())}",
        )
    try:
        return await checker()
    except Exception as exc:
        logger.exception("Fout bij testen van %s: %s", service_name, exc)
        raise HTTPException(status_code=500, detail=f"Test mislukt: {exc}")


@router.get("/settings", response_model=list[SettingResponse])
async def get_settings():
    """Haal alle instellingen op, met gemaskeerde waarden voor gevoelige sleutels."""
    all_settings = settings_manager.get_all()
    result = []
    for key, value in all_settings.items():
        masked = _mask_value(key, value)
        result.append(
            SettingResponse(
                key=key,
                value=value if key not in _SENSITIVE_KEYS else "",
                masked_value=masked,
            )
        )
    return result


@router.post("/settings", response_model=SettingResponse)
async def save_setting(data: SettingUpdate):
    """Sla een instelling op (insert of update)."""
    settings_manager.set(key=data.key, value=data.value, description=data.description)
    masked = _mask_value(data.key, data.value)
    return SettingResponse(
        key=data.key,
        value=data.value if data.key not in _SENSITIVE_KEYS else "",
        description=data.description,
        masked_value=masked,
    )


@router.delete("/settings/{key}")
async def delete_setting(key: str):
    """Verwijder een instelling uit de database."""
    deleted = settings_manager.delete(key)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Instelling '{key}' niet gevonden.")
    return {"detail": f"Instelling '{key}' verwijderd."}
