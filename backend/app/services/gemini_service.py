"""Google Gemini API integratie voor AI-Studio.

Biedt scriptgeneratie voor kindervideo's, SEO-optimalisatie,
beeldprompt-uitbreiding, Imagen 3 en Google Cloud TTS fallback.
Dynamische configuratie: haalt bij elke aanroep vers de API-sleutel
uit SQLite / /data/config.json met .strip() sanitization.
"""

import base64
import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)

# Actuele Gemini modellen (2025/2026 standaard):
_TEXT_MODEL_CANDIDATES = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]
_FAST_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]
_IMAGEN_MODEL = "imagen-3.0-generate-002"


def _clean_json_text(raw: str) -> str:
    """Verwijder markdown-fences en omringende tekst rond een JSON-object."""
    text = raw.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    match = re.search(r"\{.*\}", text, re.DOTALL)
    return match.group(0) if match else text


class GeminiService:
    """Service voor interactie met de Google Gemini API en Imagen."""

    def __init__(self, api_key: Optional[str] = None):
        self._custom_key = api_key.strip() if api_key else None
        self._configured_key: Optional[str] = None
        current_key = self.get_api_key()
        if current_key:
            self._configure(current_key)

    def get_api_key(self) -> str:
        """Haal de actieve Gemini API-sleutel vers op uit de settings database."""
        if self._custom_key:
            return self._custom_key.strip()
        key = settings_manager.get("gemini_api_key", settings.gemini_api_key) or ""
        return key.strip()

    def _configure(self, api_key: str) -> None:
        clean_key = api_key.strip()
        if clean_key and clean_key != self._configured_key:
            try:
                import google.generativeai as genai

                genai.configure(api_key=clean_key)
                self._configured_key = clean_key
            except Exception as exc:
                logger.warning("Fout bij configureren google.generativeai: %s", exc)

    def _ensure_configured(self) -> str:
        """Controleer of de Gemini API-sleutel is ingesteld en configureer dynamisch."""
        current_key = self.get_api_key()
        if not current_key:
            raise ValueError(
                "Gemini API-sleutel is niet geconfigureerd. "
                "Stel deze in via het Setup Centrum (http://localhost:3000/setup)."
            )
        self._configure(current_key)
        return current_key

    async def test_api_key(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Test een Gemini API-sleutel via het officiële models-endpoint.
        
        Geeft een lijst van daadwerkelijk beschikbare modellen terug en
        nauwkeurige foutcodes bij problemen.
        """
        key_to_test = (api_key.strip() if api_key else self.get_api_key())
        if not key_to_test:
            return {
                "valid": False,
                "status_code": 400,
                "models": [],
                "text_models": [],
                "image_models": [],
                "message": "Geen API-sleutel opgegeven.",
                "error": "Vul een geldige Gemini API-sleutel in.",
            }

        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key_to_test}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)

                if resp.status_code == 200:
                    data = resp.json()
                    raw_models = data.get("models", [])
                    all_model_names = [
                        m.get("name", "").replace("models/", "")
                        for m in raw_models
                        if m.get("name")
                    ]

                    # Filter handige tekst- en beeldmodellen voor de UI dropdown
                    text_models = [
                        m for m in all_model_names
                        if "gemini" in m.lower() and not "embedding" in m.lower() and not "aqa" in m.lower()
                    ]
                    # Sorteer zodat 2.5 en 2.0 bovenaan staan
                    text_models.sort(reverse=True)

                    image_models = [
                        m for m in all_model_names
                        if "imagen" in m.lower() or "image" in m.lower()
                    ]
                    if not image_models:
                        image_models = ["imagen-3.0-generate-002"]

                    # Configureer direct met deze geldige sleutel
                    self._configure(key_to_test)

                    return {
                        "valid": True,
                        "status_code": 200,
                        "models": all_model_names,
                        "text_models": text_models or _TEXT_MODEL_CANDIDATES,
                        "image_models": image_models,
                        "message": f"Gemini API-verbinding succesvol! {len(text_models)} modellen beschikbaar.",
                        "error": None,
                    }
                else:
                    # Google geeft gestructureerde foutmeldingen terug
                    try:
                        err_data = resp.json()
                        err_msg = err_data.get("error", {}).get("message", resp.text)
                        err_status = err_data.get("error", {}).get("status", f"HTTP_{resp.status_code}")
                    except Exception:
                        err_msg = resp.text[:300]
                        err_status = f"HTTP_{resp.status_code}"

                    return {
                        "valid": False,
                        "status_code": resp.status_code,
                        "models": [],
                        "text_models": [],
                        "image_models": [],
                        "message": "Verbinding met Gemini API mislukt.",
                        "error": f"Google API Fout ({resp.status_code} {err_status}): {err_msg}",
                    }
        except httpx.ConnectError as ce:
            logger.warning("Gemini verbindingsfout: %s", ce)
            return {
                "valid": False,
                "status_code": 503,
                "models": [],
                "text_models": [],
                "image_models": [],
                "message": "Kan Google Gemini API servers niet bereiken.",
                "error": f"Netwerkfout bij verbinden naar generativelanguage.googleapis.com: {ce}",
            }
        except Exception as exc:
            logger.warning("Onverwachte fout bij testen Gemini sleutel: %s", exc)
            return {
                "valid": False,
                "status_code": 500,
                "models": [],
                "text_models": [],
                "image_models": [],
                "message": "Onverwachte fout bij verificatie.",
                "error": str(exc),
            }

    async def _generate_text(
        self,
        prompt: str,
        model_candidates: Optional[List[str]] = None,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        json_mode: bool = False,
        safety_settings: Optional[Dict[Any, Any]] = None,
    ) -> str:
        """Genereer tekst met automatische fallback tussen Gemini-modellen."""
        import google.generativeai as genai

        self._ensure_configured()
        
        # Kijk of gebruiker een voorkeursmodel heeft opgeslagen
        preferred_model = settings_manager.get("gemini_model", "").strip()
        candidates = list(model_candidates or _FAST_MODEL_CANDIDATES)
        if preferred_model and preferred_model not in candidates:
            candidates.insert(0, preferred_model)
        elif preferred_model and preferred_model in candidates:
            candidates.remove(preferred_model)
            candidates.insert(0, preferred_model)

        last_error: Optional[Exception] = None

        generation_config: Dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_output_tokens,
        }
        if json_mode:
            generation_config["response_mime_type"] = "application/json"

        for model_name in candidates:
            try:
                model = genai.GenerativeModel(model_name)
                response = await model.generate_content_async(
                    prompt,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                text = getattr(response, "text", "") or ""
                if text.strip():
                    return text.strip()
                last_error = RuntimeError(f"Leeg antwoord van model {model_name}")
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Gemini model %s faalde (%s); probeer volgend model.",
                    model_name,
                    exc,
                )

        raise RuntimeError(f"Geen enkel Gemini-model beschikbaar: {last_error}")

    async def generate_script(
        self,
        topic: str,
        target_age_min: int = 3,
        target_age_max: int = 7,
        duration_minutes: int = 12,
        language: str = "nl",
        characters: Optional[List[str]] = None,
        style: str = "educatief en speels",
        additional_instructions: str = "",
    ) -> Dict[str, Any]:
        """Genereer een compleet educatief script voor een kindervideo.

        Berekent het aantal scènes op basis van ~8-15 seconden per scène.
        Geeft gestructureerde JSON terug met scènes, gesproken tekst en visuele prompts.
        """
        self._ensure_configured()
        total_seconds = duration_minutes * 60
        target_scene_count = max(8, total_seconds // 12)

        char_str = ", ".join(characters) if characters else "Vrolijke leerzame vriendjes"

        system_prompt = (
            f"Je bent een top-scenarioschrijver voor educatieve kinderprogramma's zoals Sesamstraat en Cocomelon. "
            f"Doelgroep: kinderen van {target_age_min} tot {target_age_max} jaar oud. "
            f"Taal: Nederlands ({language}). "
            f"Belangrijke pedagogische regels:\n"
            f"- Eenvoudige, ritmische, enthousiaste zinnen van maximaal 12 woorden.\n"
            f"- Interactief: stel regelmatig vragen aan de kijkertjes ('Zie jij de rode appel?').\n"
            f"- Absoluut GEEN enge, gewelddadige of conflictueuze elementen.\n"
            f"- Positieve bekrachtiging, vrolijkheid en humor.\n"
            f"- Gebruik de vaste afleveringsstructuur: hook, intro, 3 hoofdstukken, "
            f"twee kijkersvragen, herhalingsliedje en outro.\n"
            f"- Verdeel het verhaal in circa {target_scene_count} opeenvolgende scènes "
            f"van circa 8-15 seconden."
        )

        user_prompt = f"""
Maak een gedetailleerd videoscript over het onderwerp: "{topic}".
Karakters: {char_str}
Stijl: {style}
Extra instructies: {additional_instructions}

Geef je antwoord UITSLUITEND als een valide JSON-object met exact deze structuur:
{{
  "title": "Aansprekende titel voor kinderen",
  "synopsis": "Korte samenvatting in 2 zinnen",
  "seo_title": "Pakkende YouTube titel (max 60 tekens) met emoji",
  "seo_description": "Educatieve YouTube beschrijving met leerdoelen",
  "seo_tags": ["kleuters", "leren", "kinderliedjes", "educatie"],
  "thumbnail_prompt": "Kleurrijke, vrolijke 3D Pixar stijl afbeelding prompt voor de thumbnail",
  "scenes": [
    {{
      "scene_number": 1,
      "title": "Korte scène titel",
      "chapter_type": "hook",
      "speaker": "Naam van het sprekende karakter",
      "narration_text": "De enthousiaste gesproken stemtekst voor deze scène.",
      "phonetic_text": "Optionele fonetische uitspraakcorrectie",
      "visual_prompt": "Gedetailleerde Engelse prompt voor AI image generator, vibrant colors, friendly style",
      "motion_prompt": "Engelse gedetailleerde bewegingsopdracht voor Veo/Wan (bv: Adam walks excitedly toward the tree, waving enthusiastically, lively 2D cartoon character animation)",
      "background_prompt": "Engelse beschrijving van de achtergrond omgeving zonder karakters",
      "animation_type": "ken_burns",
      "transition_type": "crossfade",
      "duration_seconds": 12.0,
      "pause_after_sec": 0.4
    }}
  ]
}}
"""

        safety_settings = None
        try:
            from google.generativeai.types import HarmBlockThreshold, HarmCategory

            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            }
        except Exception:
            safety_settings = None

        raw_text = await self._generate_text(
            f"{system_prompt}\n\n{user_prompt}",
            model_candidates=_TEXT_MODEL_CANDIDATES,
            temperature=0.7,
            max_output_tokens=16384,
            json_mode=True,
            safety_settings=safety_settings,
        )

        parsed = json.loads(_clean_json_text(raw_text))
        if not isinstance(parsed.get("scenes"), list) or not parsed["scenes"]:
            raise RuntimeError("Gemini retourneerde geen geldige scènes.")
        return parsed

    async def generate_seo(
        self,
        title: str = "",
        description: str = "",
        script: str = "",
        language: str = "nl",
    ) -> Dict[str, Any]:
        """Genereer geoptimaliseerde YouTube SEO metadata voor kindervideo's."""
        self._ensure_configured()
        prompt = f"""
Als YouTube Kids SEO/GEO specialist, genereer de beste metadata voor deze kindervideo:
Titel: {title}
Beschrijving: {description}
Script excerpt: {script[:2500]}
Taal: {language}

Geef UITSLUITEND een JSON-object terug:
{{
  "seo_title": "Virale, kindvriendelijke titel met emoji (max 70 karakters)",
  "seo_description": "Uitgebreide beschrijving met AI-samenvatting, leerdoelen, hoofdstuk-tijdcodes en hashtags",
  "seo_tags": ["lijst", "met", "15-20", "relevante", "zoekwoorden"],
  "thumbnail_prompt": "Engelse prompt voor een vrolijke, kleurrijke YouTube-thumbnail met het hoofdkarakter"
}}
"""
        raw_text = await self._generate_text(
            prompt,
            model_candidates=_FAST_MODEL_CANDIDATES,
            temperature=0.6,
            max_output_tokens=4096,
            json_mode=True,
        )
        try:
            return json.loads(_clean_json_text(raw_text))
        except Exception as exc:
            logger.warning("SEO JSON parse mislukt (%s); gebruik fallback.", exc)
            return {
                "seo_title": title,
                "seo_description": description,
                "seo_tags": ["kinderen", "leren", "educatief"],
                "thumbnail_prompt": "",
            }

    async def generate_image_prompt(
        self,
        scene_description: str,
        style: str = "3d Pixar vibrant cute cartoon",
        characters: Optional[List[str]] = None,
    ) -> str:
        """Genereer een geoptimaliseerde Engelse prompt voor beeldgeneratie."""
        chars_text = ", ".join(characters) if characters else "cheerful cute friendly kid character"
        prompt = (
            f"Vertaal en optimaliseer deze scène-beschrijving naar een professionele Engelse prompt voor Stable Diffusion / Imagen:\n"
            f"Scène: {scene_description}\n"
            f"Stijl: {style}\n"
            f"Karakters: {chars_text}\n"
            f"Regels: Geen tekst in afbeelding, felle primaire kleuren, veilige kindvriendelijke animatie stijl.\n"
            f"Geef alleen de uiteindelijke Engelse prompt terug als één enkele alinea."
        )
        return await self._generate_text(
            prompt,
            model_candidates=_FAST_MODEL_CANDIDATES,
            temperature=0.4,
            max_output_tokens=512,
        )

    async def generate_scene_motion_prompt(
        self,
        scene_description: str,
        narration: str = "",
        characters: Optional[List[str]] = None,
        animation_style: str = "vibrant 2D cartoon animation, fluid character actions",
    ) -> str:
        """Genereert een actiegerichte Engelse motion prompt voor Google Veo en Wan 2.1."""
        chars_text = ", ".join(characters) if characters else "characters"
        prompt = (
            f"Write a specific, cinematic English motion prompt for an Image-to-Video AI model (Google Veo / Wan 2.1).\n"
            f"The image already depicts the scene and characters. Describe ONLY how the characters and scene MOVE.\n"
            f"Characters in scene: {chars_text}\n"
            f"Scene Context: {scene_description}\n"
            f"Narration / Dialogue: {narration}\n"
            f"Style: {animation_style}\n"
            f"Animation Requirements:\n"
            f"- Describe clear, lively actions: walking, jumping, pointing, smiling, nodding, waving, clapping.\n"
            f"- Make it energetic and suitable for a viral toddler/kids educational video.\n"
            f"- Max 2 sentences, pure English motion description without preamble or quotes."
        )
        return await self._generate_text(
            prompt,
            model_candidates=_FAST_MODEL_CANDIDATES,
            temperature=0.6,
            max_output_tokens=256,
        )

    async def generate_image_prompt_with_dna(
        self,
        scene_description: str,
        characters_dna: List[Dict[str, str]],
        global_style: str = "3D Pixar style cute friendly animation, vibrant saturated colors",
    ) -> str:
        """Bouwt een Start-Frame prompt waarin het exacte Visuele DNA van alle karakters is verankerd."""
        char_descriptions = []
        for c in characters_dna:
            name = c.get("name", "Character")
            pos = c.get("position", "center")
            dna = c.get("visual_dna", "") or c.get("description", "")
            char_descriptions.append(
                f"- {name} (positioned on the {pos} of the frame): {dna}"
            )
        chars_block = "\n".join(char_descriptions) if char_descriptions else "Cheerful friendly kids cartoon character"

        prompt = (
            f"Compose a detailed 16:9 widescreen Start-Frame prompt for an AI image generator.\n"
            f"Global Art Style: {global_style}\n"
            f"Scene Setting & Composition: {scene_description}\n"
            f"Character Visual Lock & Placement:\n{chars_block}\n"
            f"Strict Rules: Keep the exact character features, clothing, and colors. Clean composition, no text or watermarks, high quality, kid-friendly.\n"
            f"Return only the final English image prompt."
        )
        return await self._generate_text(
            prompt,
            model_candidates=_FAST_MODEL_CANDIDATES,
            temperature=0.4,
            max_output_tokens=512,
        )

    async def generate_with_imagen(
        self,
        prompt: str,
        width: int = 1920,
        height: int = 1080,
    ) -> bytes:
        """Genereer een afbeelding met Imagen 3 via de REST API."""
        api_key = self._ensure_configured()

        aspect_ratio = "16:9" if width >= height else "1:1"
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{_IMAGEN_MODEL}:predict?key={api_key}"
        )
        payload = {
            "instances": [{"prompt": prompt}],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": aspect_ratio,
                "safetyFilterLevel": "block_medium_and_above",
                "personGeneration": "allow_adult",
            },
        }

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Imagen API fout ({resp.status_code}): {resp.text[:300]}"
                )
            data = resp.json()
            predictions = data.get("predictions", [])
            if not predictions:
                raise RuntimeError("Imagen retourneerde geen afbeelding.")
            encoded = predictions[0].get("bytesBase64Encoded")
            if not encoded:
                raise RuntimeError("Imagen-antwoord bevat geen afbeeldingsdata.")
            return base64.b64decode(encoded)

    async def text_to_speech_google(
        self,
        text: str,
        voice_id: str = "nl-NL-Wavenet-A",
        language: str = "nl",
    ) -> bytes:
        """Zet tekst om naar spraak via Google Cloud Text-to-Speech REST API."""
        api_key = (
            settings_manager.get("google_tts_api_key", settings.google_tts_api_key)
            or self.get_api_key()
        )
        if not api_key:
            raise ValueError("Google TTS API sleutel ontbreekt.")

        url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"
        payload = {
            "input": {"text": text},
            "voice": {
                "languageCode": "nl-NL" if language.startswith("nl") else "en-US",
                "name": voice_id if voice_id else "nl-NL-Wavenet-A",
            },
            "audioConfig": {
                "audioEncoding": "MP3",
                "speakingRate": 0.95,
                "pitch": 2.0,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Google TTS fout ({resp.status_code}): {resp.text}")
            data = resp.json()
            return base64.b64decode(data["audioContent"])

    async def test_connection(self) -> bool:
        """Lichtgewicht live-check van de Gemini API-sleutel."""
        res = await self.test_api_key()
        return res.get("valid", False)


gemini_service = GeminiService()
