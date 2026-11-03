"""FastAPI hoofdapplicatie voor AI-Studio.

Beheert lifecycle, database initialisatie, CORS, static file serving
en registreert alle modulaire API-routers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.audio import router as audio_router, top_audio_router
from app.api.characters import router as characters_router
from app.api.direct_routes import router as direct_router
from app.api.episodes import router as episodes_router
from app.api.events import router as events_router
from app.api.generate import router as generate_router
from app.api.projects import router as projects_router
from app.api.publish import router as publish_router
from app.api.render import router as render_router
from app.api.scenes import router as scenes_router
from app.api.setup import router as setup_router
from app.core.config import settings
from app.core.database import init_db
from app.schemas.schemas import HealthResponse

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ai_studio")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialisatie bij opstarten en opschonen bij afsluiten."""
    logger.info("AI-Studio opstarten...")

    # Zorg dat alle opslagmappen bestaan in het Docker volume
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    settings.characters_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_dir.mkdir(parents=True, exist_ok=True)
    settings.images_dir.mkdir(parents=True, exist_ok=True)
    settings.renders_dir.mkdir(parents=True, exist_ok=True)
    settings.sprites_dir.mkdir(parents=True, exist_ok=True)
    settings.clips_dir.mkdir(parents=True, exist_ok=True)
    settings.exports_dir.mkdir(parents=True, exist_ok=True)
    settings.temp_dir.mkdir(parents=True, exist_ok=True)

    # Initialiseer SQLite tabellen
    try:
        init_db()
        logger.info("Database tabellen succesvol geïnitialiseerd.")
    except Exception as e:
        logger.exception("Fout bij database initialisatie: %s", e)

    yield

    logger.info("AI-Studio afgesloten.")


app = FastAPI(
    title="AI-Studio API",
    description="Productie-klare KidsEdu Viral Video Web-App API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuratie voor lokale ontwikkeling en Coolify reverse proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serveer persistente media bestanden (afbeeldingen, audio, renders, sprites)
app.mount("/api/media", StaticFiles(directory=str(settings.media_dir)), name="api_media")
app.mount("/media", StaticFiles(directory=str(settings.media_dir)), name="media")

# Registreer routers
app.include_router(setup_router)
app.include_router(projects_router)
app.include_router(characters_router)
app.include_router(episodes_router)
app.include_router(scenes_router)
app.include_router(audio_router)
app.include_router(top_audio_router)
app.include_router(render_router)
app.include_router(publish_router)
app.include_router(events_router)
app.include_router(generate_router)
app.include_router(direct_router)


@app.get("/api/health", response_model=HealthResponse, tags=["Health"])
@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint voor Docker en Coolify orchestrators."""
    return HealthResponse(status="ok", version="1.0.0")

