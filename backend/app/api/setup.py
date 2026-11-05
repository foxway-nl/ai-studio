"""Setup Centrum router – service status, connecties testen en instellingen beheren."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.core.config import settings
from app.core.database import get_session
from app.core.settings_manager import settings_manager
from app.schemas.schemas import (
    GeminiTestRequest,
    GeminiTestResponse,
    ServiceStatus,
    SettingResponse,
    SettingUpdate,
    SetupStatusResponse,
    YouTubeChannelResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/setup", tags=["Setup"])

# Sleutels die gemaskeerd moeten worden in de UI
_SENSITIVE_KEYS = {
    "gemini_api_key",
    "groq_api_key",
    "hf_token",
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
    from app.services.gemini_service import gemini_service

    api_key = gemini_service.get_api_key()
    status = ServiceStatus(
        name="Gemini",
        instructions_nl=(
            "Stel je Gemini API-sleutel in via het Setup Centrum. "
            "Ga naar https://aistudio.google.com/apikey om een gratis sleutel aan te maken."
        ),
    )
    if not api_key:
        return status
    status.configured = True
    try:
        res = await gemini_service.test_api_key(api_key)
        status.connected = res.get("valid", False)
        if not status.connected:
            status.error = res.get("error") or "Gemini API-sleutel is ongeldig of quota overschreden."
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
            "Optioneel: installeer Stable Diffusion WebUI Forge lokaal en start met --api vlag op poort 7860. "
            "Niet vereist als je Google Gemini / Imagen of de ingebouwde cloud generator gebruikt."
        ),
    )
    if not base_url:
        return status
    status.configured = True
    try:
        import httpx

        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{base_url}/sdapi/v1/options")
            status.connected = resp.status_code == 200
            if not status.connected:
                status.error = f"HTTP status {resp.status_code}"
    except (httpx.ConnectError, httpx.ConnectTimeout):
        status.error = (
            "SD WebUI Forge draait momenteel niet op poort 7860. "
            "Schakel over naar 'Google Gemini / Imagen' of 'Ingebouwde Cloud Generator' als je Forge niet lokaal gebruikt."
        )
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
    """Controleer YouTube API configuratie en actieve OAuth koppeling."""
    from app.services.youtube_service import youtube_service

    client_id = settings_manager.get("youtube_client_id", settings.youtube_client_id)
    client_secret = settings_manager.get("youtube_client_secret", settings.youtube_client_secret)
    token = settings_manager.get("youtube_oauth_token")

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

    if token:
        try:
            channel_info = youtube_service.get_channel_info()
            if channel_info:
                status.connected = True
                status.instructions_nl = f"Gekoppeld met kanaal: {channel_info.get('title')}"
            else:
                status.connected = True
        except Exception:
            status.connected = True
    else:
        status.connected = False
        status.instructions_nl = "OAuth client geconfigureerd. Koppel je account via de login knop."
    return status


async def _check_groq() -> ServiceStatus:
    """Controleer Groq Cloud Free Tier verbinding."""
    from app.services.groq_service import groq_service

    key = groq_service.get_api_key()
    status = ServiceStatus(
        name="Groq Cloud",
        instructions_nl="Gratis snelheidskanon voor Llama 3.3 70B & Whisper. Maak een gratis sleutel op console.groq.com/keys.",
    )
    if not key:
        return status
    status.configured = True
    res = await groq_service.check_connection(key)
    status.connected = res.get("connected", False)
    if not status.connected:
        status.error = res.get("error") or "Ongeldige Groq API-sleutel"
    return status


async def _check_huggingface() -> ServiceStatus:
    """Controleer Hugging Face Free Tier & ZeroGPU verbinding."""
    from app.services.huggingface_service import huggingface_service

    tok = huggingface_service.get_token()
    status = ServiceStatus(
        name="Hugging Face",
        instructions_nl="Gratis FLUX.1-schnell beeldgeneratie & ZeroGPU video-animatie. Maak een gratis token op huggingface.co/settings/tokens.",
    )
    if not tok:
        return status
    status.configured = True
    res = await huggingface_service.check_connection(tok)
    status.connected = res.get("connected", False)
    if not status.connected:
        status.error = res.get("error") or "Ongeldig Hugging Face token"
    return status


async def _check_edge_tts() -> ServiceStatus:
    """Controleer Microsoft Edge TTS beschikbaarheid."""
    return ServiceStatus(
        name="Edge TTS",
        configured=True,
        connected=True,
        instructions_nl="Standaard actief & gratis: Hoogwaardige Nederlandse kinderstemmen (o.a. Fenna en Maarten).",
    )


_SERVICE_CHECKERS = {
    "gemini": _check_gemini,
    "groq": _check_groq,
    "huggingface": _check_huggingface,
    "edge_tts": _check_edge_tts,
    "ollama": _check_ollama,
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


@router.post("/test-gemini", response_model=GeminiTestResponse)
async def test_gemini_api(data: Optional[GeminiTestRequest] = None):
    """Valideer een Gemini API-sleutel en haal actuele beschikbare modellen op."""
    from app.services.gemini_service import gemini_service

    api_key = data.api_key.strip() if (data and data.api_key) else None
    res = await gemini_service.test_api_key(api_key=api_key)

    # Als de test slaagt en er werd een echte (niet-gemaskeerde) sleutel meegegeven, sla hem direct op
    if res.get("valid") and api_key and not settings_manager.is_masked_value(api_key):
        settings_manager.set("gemini_api_key", api_key, "Google Gemini API sleutel")

    return GeminiTestResponse(
        valid=res.get("valid", False),
        status_code=res.get("status_code", 400),
        models=res.get("models", []),
        text_models=res.get("text_models", []),
        image_models=res.get("image_models", []),
        video_models=res.get("video_models", []),
        tts_models=res.get("tts_models", []),
        message=res.get("message", ""),
        error=res.get("error"),
    )


@router.get("/models")
async def get_discovered_models():
    """Haal de live ontdekte modellen op uit de configuratie."""
    raw = settings_manager.get("gemini_discovered_models")
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            pass

    key = settings_manager.get("gemini_api_key")
    if key and not settings_manager.is_masked_value(key):
        try:
            from app.services.gemini_service import discover_available_models
            discovered = discover_available_models(key)
            settings_manager.set("gemini_discovered_models", json.dumps(discovered))
            return discovered
        except Exception:
            pass

    return {
        "text_models": ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
        "image_models": ["imagen-3.0-generate-002"],
        "video_models": ["veo-2.0-generate-001"],
        "tts_models": [],
    }


@router.get("/youtube-channel", response_model=YouTubeChannelResponse)
async def get_youtube_channel():
    """Haal profiel en statistieken op van het actieve gekoppelde YouTube account."""
    from app.services.youtube_service import youtube_service

    info = youtube_service.get_channel_info()
    if not info:
        return YouTubeChannelResponse(connected=False)
    return YouTubeChannelResponse(**info)


@router.post("/youtube-disconnect")
async def disconnect_youtube():
    """Ontkoppel het gekoppelde YouTube account."""
    from app.services.youtube_service import youtube_service

    youtube_service.disconnect()
    return {"detail": "YouTube account succesvol ontkoppeld."}


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
