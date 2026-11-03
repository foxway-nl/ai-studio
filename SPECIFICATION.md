# SOFTWARE REQUIREMENTS SPECIFICATION (SRS): KidsEdu Viral Video Studio

## 1. Projectoverzicht & Doelstelling
Bouw een professionele, lokaal gehoste full-stack web-applicatie ("KidsEdu Studio") voor het produceren, beheren, verfijnen en publiceren van educatieve, virale YouTube-video's van 10 tot 15 minuten voor kinderen tot 7 jaar.
De applicatie combineert een strikte "Audio-First" virale workflow met volledige handmatige controle (Human-in-the-Loop), automatische status-opslag (zodat de gebruiker op elk moment kan stoppen en later verder kan gaan) en directe YouTube-publicatie.

---

## 2. Systeemarchitectuur & Tech Stack (Open-Source + Gemini Pro)
De AI-agent dient de volgende modulaire architectuur op te zetten:

* **Frontend:** React (Next.js of Vite) + TailwindCSS + Zustand (state management) + Lucide Icons. Overzichtelijke dark/light studio-interface.
* **Backend:** Python **FastAPI** (asynchroon).
* **Database & Opslag (Persistentie):**
  * **SQLite** (met SQLAlchemy / SQLModel) voor het opslaan van projecten, afleveringen, scènes, versies, karakter-presets en instellingen.
  * **Lokale Bestandsopslag (`/storage/episodes/{episode_id}/`):** Georganiseerd in submappen `/audio`, `/images`, `/sprites`, `/renders` en een gesynchroniseerde `manifest.json`.
  * **Auto-Save:** Elke wijziging in tekst, prompts, timing of instellingen wordt direct (debounced < 500ms) opgeslagen in SQLite.
* **Taakwachtrij (Background Worker):** Asynchrone Python task queue (bijv. `ARQ`, `Celery` of FastAPI background tasks met status-polling via WebSockets/SSE) zodat bulk-generatie van audio, beelden en FFmpeg-renders nooit de UI blokkeert en hervat kan worden na een herstart.
* **AI & Media Engines:**
  1. **Master Script, Educatieve Controle & SEO/GEO:** Google **Gemini Pro API** (`google-genai` SDK met Structured JSON Outputs).
  2. **Lokale Prompt-Verfijning & Snelle Vertaling:** **Ollama API** (`http://localhost:11434`, bijv. `qwen2.5` of `llama3.1`).
  3. **Text-to-Speech (TTS):**
     * Primair (NL/Meertalig): Google Cloud TTS / Gemini Audio API of lokale **F5-TTS** / **Piper TTS** / **Kokoro-82M**.
     * Ondersteuning voor een `phonetic_text` veld per scène om uitspraakfouten handmatig te corrigeren.
  4. **Audio-Analyse & Timestamps:** Lokaal **faster-whisper** / **WhisperX** + `pydub` / `librosa` voor exacte zin-timestamps, stiltedetectie en volume-analyse (voor mond-animatie).
  5. **Beeldgeneratie (Zonder ComfyUI-complexiteit):**
     * **Engine 1 (Lokaal):** **Stable Diffusion WebUI Forge** (`--api` modus op `/sdapi/v1/txt2img`) met ondersteuning voor een vaste Style-LoRA en ControlNet `IP-Adapter` voor karakterbehoud.
     * **Engine 2 (Cloud Fallback/Kwaliteit):** **Google Imagen 3 API** (via `google-genai` SDK).
     * **Engine 3 (2.5D Compositor):** Python `Pillow` / `MoviePy` laag die transparante PNG-sprites van vaste hoofdpersonen (met verschillende emoties en open/dichte mond) over gegenereerde AI-achtergronden plaatst.
  6. **Video Rendering Engine:** **FFmpeg** (aangestuurd via Python) voor 2.5D Ken Burns-bewegingen, overgangen, ondertiteling/visuele tellers en professionele audiomixing.

---

## 3. Vaste Aflevering-Structuur & "Viral Guardrails" (Validatie-Engine)
Elke aflevering volgt een bewezen educatieve structuur voor kinderen < 7 jaar en bevat verplichte vaste elementen. De applicatie bevat een **"Viral Coach / Guardrail Engine"** die real-time waarschuwingen geeft in de UI als de gebruiker afwijkt van de richtlijnen:

### 3.1 Vaste Aflevering-Blokken (Sjabloon)
Bij het aanmaken van een nieuwe aflevering genereert het systeem automatisch deze vaste hoofdstuk-indeling:
1. **Cold Open / De Haak (00:00 - 00:45):** Directe visuele prikkel en nieuwsgierigheidsvraag (geen lange intro vooraf).
2. **Vaste Intro Bumper (00:45 - 00:55):** Automatisch ingevoegd vast intro-filmpje (`assets/fixed/intro_bumper.mp4`).
3. **Hoofdstuk 1: Ontdekking 1 (00:55 - 03:30):** Introductie van het thema met visuele voorbeelden.
4. **Interactieve Kijkersvraag 1 (vast element):** Karakter kijkt in de camera, stelt een vraag, gevolgd door een vaste **3-seconden visuele aftelklok + tik-geluid** en beloningsgeluid (*"Goed zo!"*).
5. **Hoofdstuk 2: Ontdekking 2 / Verdieping (03:30 - 07:00):** Nieuw locatie-element of spelvorm (bijv. tellen, kleuren zoeken, vormen raden).
6. **Interactieve Kijkersvraag 2 (vast element):** Tweede doe-moment met 3-seconden pauze.
7. **Hoofdstuk 3: De Oplossing & Herhaling (07:00 - 10:30):** Samenbrengen van wat geleerd is.
8. **Vast Herhalingsliedje / Samenvatting (10:30 - 11:30):** Ritmische samenvatting van de leerdoelen.
9. **Vaste Outro Bumper (11:30 - 12:00):** Vaste afsluiter (`assets/fixed/outro_bumper.mp4`).

### 3.2 Automatische Guardrails (Waarschuwingen in het Dashboard)
De UI toont een geel/rood waarschuwingsicoon bij een scène of aflevering als:
* **Visuele stilstand > 7 seconden:** Een scène heeft een audiobestand langer dan 7 seconden zonder camera-actie of sub-scène wissel (*Advies: "Splits deze scène op voor jonge kijkers"*).
* **Te moeilijke zinnen:** Een zin bevat meer dan 15 woorden of abstracte begrippen (*Advies: "Houd zinnen kort en beeldend voor kinderen tot 7 jaar"*).
* **Geen interactie:** Er zit langer dan 3 minuten geen directe kijkersvraag of geluidseffect in het script.
* **Totale duur buiten bereik:** De opgetelde audioduur is korter dan 8 minuten of langer dan 16 minuten.

---

## 4. De 6-Stappen Workflow in de Web-Applicatie

### Stap 1: Dashboard & Aflevering Beheer
* Overzicht van alle afleveringen met status-badges (`Draft`, `Script Klaar`, `Audio Klaar`, `Beelden Klaar`, `Gerenderd`, `Gepubliceerd op YouTube`).
* Mogelijkheid om een bestaande aflevering te openen en exact verder te gaan waar gebleven, of te dupliceren als template.

### Stap 2: Karakters, Stijl & Vaste Elementen Bibliotheek (Globaal)
* **Character Manager:** Upload en beheer vaste hoofdpersonen (bijv. Adam en Nora). Koppel per karakter:
  * Vaste stem-ID en spraaksnelheid.
  * Vaste visuele prompt-beschrijving + IP-Adapter referentieplaatjes.
  * **2D Sprite Map:** Transparante PNG's per emotie (`blij`, `verbaasd`, `denkend`, `wijzend`) met een `mouth_closed.png` en `mouth_open.png` voor automatische lip-sync.
* **Style Preset:** Vaste prefix en negative prompt die automatisch aan élke gegenereerde achtergrond/afbeelding wordt toegevoegd.

### Stap 3: Script & Scène-Editor (Gemini Pro + Handmatig Fine-tunen)
* Voer een onderwerp en leerdoel in (bijv. *"Leren hoe bijen honing maken en tellen tot 5"*).
* Gemini Pro genereert het volledige script opgedeeld in 100-140 scènes binnen de vaste hoofdstukken.
* **Volledige Handmatige Controle:**
  * Scènes toevoegen, verwijderen, splitsen of van volgorde veranderen (drag & drop).
  * Tekst aanpassen, emotie kiezen via dropdown, en optioneel `Fonetische Uitspraak` invullen.

### Stap 4: Audio-First Studio & Timing (TTS + WhisperX)
* Knop **"Genereer Alle Audio"** én per scène een knop **"Regenereer Audio"** of **"Upload Eigen Stemopname"**.
* Automatische berekening van exacte duur per scène + instelbare stiltetijd na de zin (`pause_after_sec`, standaard `0.4s`, na een kijkersvraag `3.0s`).
* Audio-waveform preview per scène in de tabel.

### Stap 5: Visuele Scène-Bouwer & Overgangen (Forge API / Imagen + 2.5D)
* **Prompt Vertaling:** Ollama of Gemini vertaalt de goedgekeurde Nederlandse scènetekst naar een Engelse beeldprompt volgens de vaste stijlregels.
* **Keuze per scène:**
  1. *Volledige AI-afbeelding* (via SD WebUI Forge REST API of Google Imagen API).
  2. *AI-achtergrond + 2D Karakter Sprite* (selecteer karakter, positie links/midden/rechts, en emotie).
* **Finetuning per scène:**
  * Prompt handmatig aanpassen en met 1 klik een nieuw plaatje genereren.
  * Vorige gegenereerde plaatjes van die scène blijven bewaard in een **Scène-Geschiedenis (History)** zodat je altijd terug kunt kiezen.
  * **Camera-beweging kiezen:** `Slow Zoom In`, `Slow Zoom Out`, `Pan Left-to-Right`, `Pan Right-to-Left`, `Static`.
  * **Overgang naar volgende scène kiezen:**
    * Standaard automatisch: `Hard Cut` (binnen een hoofdstuk) en `Cross-Dissolve / Circle Wipe + Whoosh SFX` (op hoofdstukgrens).
    * Handmatig per scène aanpasbaar via dropdown (`Hard Cut`, `Cross-Dissolve`, `Circle Wipe`, `Slide Left`, `Dip to White`, `Star Bumper`).

### Stap 6: Video Assemblage, SEO/GEO Generator & YouTube Push
* **Render Engine (FFmpeg):**
  * Voegt vaste Intro/Outro bumpers, scènes, overgangen, 2D praat-animaties (op basis van audio-amplitude) en geluidseffecten samen.
  * **Audio-Mixing:** Spraak op `-3 dB`, SFX op `-12 dB`, achtergrondmuziek met automatische *sidechain ducking* (`-24 dB` tijdens spraak, `-14 dB` tijdens stiltes), master normalisatie op `-14 LUFS`.
  * Rendert een `preview_480p.mp4` (supersnel om te controleren) of `master_1080p_60fps.mp4`.
* **SEO & GEO Metadata Studio (Gemini Pro):**
  * Genereert op basis van het definitieve script en de exacte Whisper-tijdstempels:
    1. **5 High-CTR Titels** (gericht op ouders én zoekintentie).
    2. **GEO- en SEO-geoptimaliseerde Beschrijving:** Inclusief samenvatting voor AI-zoekmachines ( antwoord op *"Wat leert mijn kind in deze video?"*), leerdoelen-lijst, exacte YouTube-hoofdstukken (`00:00 Intro`, etc.) en relevante zoekwoorden.
    3. **15-20 Tags** en **5 Thumbnail Prompts** (inclusief 1-klik generatie van de thumbnails in de app).
  * Alle SEO-velden zijn handmatig te bewerken.
* **Directe YouTube Upload Knop (YouTube Data API v3):**
  * Gebruikt OAuth 2.0 met het *Resumable Upload Protocol* (`videos.insert` in chunks van 256 KB) en `thumbnails.set` voor de gekozen thumbnail.
  * **Verplichte Kindercontent-instelling:** Zet `status.selfDeclaredMadeForKids = true` standaard aan.
  * Keuze voor publicatiestatus: `Private`, `Unlisted`, `Public` of `Scheduled (Ingeroosterd op datum/tijd)`.

---

## 5. Datamodel Schema (SQLite Overzicht voor de Agent)
De AI-agent moet minimaal deze 3 kerntabellen aanmaken:
1. `episodes`: `id`, `title`, `theme`, `learning_goals`, `status`, `bg_music_track`, `seo_title`, `seo_description`, `seo_tags`, `thumbnail_path`, `youtube_video_id`, `created_at`, `updated_at`.
2. `scenes`: `id`, `episode_id`, `scene_order`, `chapter_type`, `speaker`, `script_text`, `phonetic_text`, `emotion`, `audio_path`, `duration_sec`, `pause_after_sec`, `image_prompt`, `image_path`, `image_history_json`, `use_2d_sprite`, `sprite_config_json`, `camera_motion`, `transition_type`, `sfx_track`, `status`.
3. `characters`: `id`, `name`, `voice_id`, `visual_trigger_prompt`, `reference_images_json`, `sprites_map_json`.

---

## 6. Bouwvolgorde voor de AI-Agent (Milestone Plan)
Bouw de applicatie niet in één gigantische commit, maar in deze 4 testbare fases:
* **Fase 1:** FastAPI + SQLite database + React Dashboard waarin afleveringen en scènes aangemaakt, bewerkt en automatisch opgeslagen worden.
* **Fase 2:** Integratie van Gemini Pro (scriptgeneratie + guardrails) en de Audio-pijplijn (TTS + automatische duurmeting + audio-afspeler per scène).
* **Fase 3:** Integratie van Beeldgeneratie (SD WebUI Forge API / Imagen API + 2D Sprite overlay) en de Scène-geschietenis UI.
* **Fase 4:** FFmpeg Render-pijplijn (inclusief overgangen en audio-ducking) + SEO/GEO generator + YouTube Data API v3 upload-knop.