# AI-Studio

> Productie-klare web-applicatie voor het maken, beheren, renderen en publiceren van virale, educatieve YouTube-video's voor kinderen tot 7 jaar.

## 🏗️ Architectuur

```
ai-studio/
├── docker-compose.yml          # Volledige stack (backend + frontend)
├── backend/                    # FastAPI (Python 3.11) + FFmpeg
│   └── app/
│       ├── main.py             # Entry point + CORS + health check
│       ├── core/               # Config, database, settings manager
│       ├── models/             # SQLModel database tabellen
│       ├── schemas/            # Pydantic v2 validatie
│       ├── services/           # Gemini, Ollama, Audio, Image, FFmpeg, YouTube, Guardrails
│       ├── workers/            # Async achtergrondtaken met SSE voortgang
│       └── api/                # FastAPI routers
└── frontend/                   # React 18 + TypeScript + Vite + TailwindCSS
    └── src/
        ├── components/         # Herbruikbare UI componenten
        ├── pages/              # Dashboard, Setup, Characters, Episode Studio, Render
        ├── store/              # Zustand state management + auto-save
        └── api/                # Typed API client
```

## 🚀 Snel Starten

### Vereisten
- Docker & Docker Compose
- (Optioneel) Ollama voor lokale LLM
- (Optioneel) Stable Diffusion WebUI Forge voor afbeeldingen

### Opstarten

```bash
# 1. Kloon de repository
git clone https://github.com/foxway-nl/ai-studio.git
cd ai-studio

# 2. Maak een .env bestand
cp .env.example .env

# 3. Start de stack
docker compose up --build -d

# 4. Open de applicatie
open http://localhost:3000
```

### Eerste Configuratie

1. Ga naar **Setup Centrum** (`http://localhost:3000/setup`)
2. Vul je API-sleutels in:
   - **Gemini API Key** — voor script generatie, SEO en TTS
   - **Ollama URL** — voor lokale prompt vertaling (optioneel)
   - **SD WebUI URL** — voor afbeelding generatie (optioneel)
   - **YouTube OAuth** — voor video publicatie (optioneel)
3. Test elke verbinding met de "Test Verbinding" knop
4. De app werkt ook zonder API-sleutels — het Setup Centrum laat zien wat je nodig hebt

## 🎯 Functionaliteiten

### 📝 Script Generatie
- AI-gegenereerde educatieve scripts via Google Gemini
- Automatische SEO-optimalisatie (titel, beschrijving, tags)
- Ingebouwde kindveiligheidschecks (guardrails)
- Ondersteuning voor meerdere talen (standaard Nederlands)

### 🎨 Visuele Content
- Afbeelding generatie via Stable Diffusion WebUI Forge of Imagen 3
- 2.5D sprite compositing met karakter expressies
- Ken Burns effecten, pan, zoom animaties
- Automatische scène-compositie met achtergrond + karakters

### 🔊 Audio Productie
- Text-to-Speech via Piper (lokaal), Google Cloud TTS of Kokoro
- Woord-level timestamps via faster-whisper
- Lip-sync animatie op basis van timestamps
- Audio mixing met sidechain ducking en -14 LUFS normalisatie

### 🎬 Video Rendering
- Volledige episode rendering via FFmpeg
- Scène-overgangen (crossfade, fade, slide, wipe)
- Real-time voortgang via Server-Sent Events
- Configureerbare resolutie en framerate

### 📺 YouTube Publicatie
- OAuth2 authenticatie met YouTube Data API v3
- Resumable video upload met voortgangstracking
- Automatische "Made for Kids" instelling
- Thumbnail upload

## 🐳 Deployment via Coolify

### Docker Compose Deployment

1. Maak een nieuw project in Coolify
2. Koppel de GitHub repository: `foxway-nl/ai-studio`
3. Selecteer "Docker Compose" als build methode
4. Stel de volgende omgevingsvariabelen in:
   - `GEMINI_API_KEY` — je Google Gemini API sleutel
   - `APP_SECRET_KEY` — een willekeurige string voor sessie-encryptie
5. Deploy!

### Poorten

| Service  | Poort | Beschrijving |
|----------|-------|-------------|
| Frontend | 3000  | Web interface (Nginx) |
| Backend  | 8000  | API server (FastAPI) |

### Volumes

De `ai_studio_data` volume bevat alle persistente data:
- `ai_studio.db` — SQLite database
- `media/` — afbeeldingen, audio, renders
- `media/characters/` — karakter sprites
- `media/audio/` — TTS audio bestanden
- `media/images/` — gegenereerde achtergronden
- `media/renders/` — gerenderde video's

## 🔧 Ontwikkeling

### Lokaal zonder Docker

```bash
# Backend
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
DATA_DIR=./data uvicorn app.main:app --reload --port 8000

# Frontend (apart terminal)
cd frontend
npm install
npm run dev
```

### Multi-architectuur

De Docker images bouwen voor zowel `linux/amd64` als `linux/arm64`:
- ✅ macOS Apple Silicon (M1/M2/M3/M4)
- ✅ Ubuntu Linux servers (via Coolify)

## 📄 Licentie

Eigendom van Foxway BV. Alle rechten voorbehouden.

