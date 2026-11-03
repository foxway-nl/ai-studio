"""Google Gemini API integratie voor AI-Studio.

Gebruikt de officiële actuele `google-genai` SDK (v1.0+).
- from google import genai
- from google.genai import types

Functionaliteit:
- Live model discovery via client.models.list() (geen gegokte modelnamen)
- Script- & SEO-generatie via client.models.generate_content
- Echte beeldgeneratie via client.models.generate_images (Imagen) of
  multimodale generate_content met referentie-afbeeldingen voor karakterconsistentie
- Directe foutafhandeling met exacte Google API foutmeldingen (geen stille fallbacks)
- Veilige sleutelreiniging en dynamische configuratie
"""

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from PIL import Image

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


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


def get_client(api_key: Optional[str] = None) -> genai.Client:
    """Maak een verse genai.Client aan met gereinigde API-sleutel."""
    raw_key = api_key or settings_manager.get("gemini_api_key", settings.gemini_api_key) or ""
    clean_key = str(raw_key).strip().strip('"').strip("'")
    if not clean_key or settings_manager.is_masked_value(clean_key):
        raise ValueError(
            "Gemini API-sleutel is niet geconfigureerd of is gemaskeerd. "
            "Vul je echte Google Gemini API-sleutel in via het Setup Centrum."
        )
    return genai.Client(api_key=clean_key)


def discover_available_models(api_key: str) -> Dict[str, List[str]]:
    """Haalt live via client.models.list() alle actuele modellen van het Google-account op."""
    clean_key = api_key.strip().strip('"').strip("'")
    client = genai.Client(api_key=clean_key)
    text_models: List[str] = []
    image_models: List[str] = []
    video_models: List[str] = []
    tts_models: List[str] = []

    for m in client.models.list():
        name = m.name.replace("models/", "")
        low = name.lower()
        if "veo" in low:
            video_models.append(name)
        elif "imagen" in low or "image" in low:
            image_models.append(name)
        elif "tts" in low or "audio" in low:
            tts_models.append(name)
        elif "gemini" in low and "embedding" not in low and "aqa" not in low:
            text_models.append(name)

    return {
        "text_models": sorted(text_models, reverse=True),
        "image_models": sorted(image_models, reverse=True),
        "video_models": sorted(video_models, reverse=True),
        "tts_models": sorted(tts_models, reverse=True),
    }


class GeminiService:
    """Centrale service voor Gemini, Imagen en Veo via de officiële google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None):
        self._custom_key = api_key.strip().strip('"').strip("'") if api_key else None

    def get_api_key(self) -> str:
        """Haal de actieve Gemini API-sleutel op uit de settings database."""
        if self._custom_key and not settings_manager.is_masked_value(self._custom_key):
            return self._custom_key
        key = settings_manager.get("gemini_api_key", settings.gemini_api_key) or ""
        return key.strip().strip('"').strip("'")

    def _get_client(self) -> genai.Client:
        return get_client(self.get_api_key())

    def _resolve_text_model(self) -> str:
        """Kiest het geconfigureerde of best beschikbare Gemini tekstmodel."""
        preferred = settings_manager.get("gemini_text_model") or settings_manager.get("gemini_model")
        if preferred and preferred.strip():
            return preferred.strip()
        # Fallback naar moderne standaarden
        return "gemini-2.5-flash"

    def _resolve_image_model(self) -> str:
        """Kiest het geconfigureerde of best beschikbare Imagen/Gemini beeldmodel."""
        preferred = settings_manager.get("gemini_image_model") or settings_manager.get("selected_image_model")
        if preferred and preferred.strip():
            return preferred.strip()
        return "imagen-3.0-generate-002"

    def _resolve_video_model(self) -> str:
        """Kiest het geconfigureerde of best beschikbare Veo model."""
        preferred = settings_manager.get("gemini_video_model") or settings_manager.get("selected_veo_model")
        if preferred and preferred.strip():
            return preferred.strip()
        return "veo-2.0-generate-001"

    async def test_api_key(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """Test de API-sleutel live via client.models.list() en retourneert actuele modellen."""
        raw_key = api_key if api_key else self.get_api_key()
        if not raw_key:
            return {
                "valid": False,
                "status_code": 400,
                "models": [],
                "text_models": [],
                "image_models": [],
                "video_models": [],
                "tts_models": [],
                "message": "Geen API-sleutel opgegeven.",
                "error": "Vul een geldige Gemini API-sleutel in.",
            }

        # Als gemaskeerde waarde werd meegestuurd, gebruik de reeds opgeslagen sleutel
        if settings_manager.is_masked_value(raw_key):
            saved = settings_manager.get("gemini_api_key")
            if saved and not settings_manager.is_masked_value(saved):
                raw_key = saved
            else:
                return {
                    "valid": False,
                    "status_code": 400,
                    "models": [],
                    "text_models": [],
                    "image_models": [],
                    "video_models": [],
                    "tts_models": [],
                    "message": "Gemaskeerde sleutel kan niet gevalideerd worden.",
                    "error": "Voer de volledige, ongemaskeerde API-sleutel in.",
                }

        clean_key = raw_key.strip().strip('"').strip("'")

        try:
            discovered = discover_available_models(clean_key)
            all_models = (
                discovered["text_models"]
                + discovered["image_models"]
                + discovered["video_models"]
                + discovered["tts_models"]
            )

            # Sla de ontdekte modellen op in de configuratie voor directe UI toegang
            settings_manager.set(
                "gemini_discovered_models",
                json.dumps(discovered),
                "Live ontdekte Google AI modellen",
            )
            # Stel default modellen in als deze nog niet geconfigureerd zijn
            if discovered["text_models"] and not settings_manager.get("gemini_text_model"):
                settings_manager.set("gemini_text_model", discovered["text_models"][0])
            if discovered["image_models"] and not settings_manager.get("gemini_image_model"):
                settings_manager.set("gemini_image_model", discovered["image_models"][0])
            if discovered["video_models"] and not settings_manager.get("gemini_video_model"):
                settings_manager.set("gemini_video_model", discovered["video_models"][0])

            return {
                "valid": True,
                "status_code": 200,
                "models": all_models,
                "text_models": discovered["text_models"],
                "image_models": discovered["image_models"],
                "video_models": discovered["video_models"],
                "tts_models": discovered["tts_models"],
                "message": f"Gemini API-verbinding succesvol! {len(discovered['text_models'])} tekstmodellen en {len(discovered['image_models'])} beeldmodellen beschikbaar.",
                "error": None,
            }
        except Exception as e:
            logger.warning("Fout bij valideren Gemini API sleutel via live discovery: %s", e)
            err_str = str(e)
            return {
                "valid": False,
                "status_code": 400,
                "models": [],
                "text_models": [],
                "image_models": [],
                "video_models": [],
                "tts_models": [],
                "message": "Google Gemini verificatie mislukt.",
                "error": f"Google API Fout: {err_str}",
            }

    async def _generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: int = 8192,
        json_mode: bool = False,
        system_instruction: Optional[str] = None,
    ) -> str:
        """Genereert tekst via client.models.generate_content."""
        client = self._get_client()
        model_name = self._resolve_text_model()

        config = types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json" if json_mode else "text/plain",
            system_instruction=system_instruction,
        )

        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            text = response.text or ""
            if not text.strip():
                raise RuntimeError(f"Model {model_name} retourneerde een leeg antwoord.")
            return text.strip()
        except Exception as e:
            logger.error("Fout bij generate_content met model %s: %s", model_name, e)
            raise RuntimeError(f"Google Gemini Fout ({model_name}): {e}") from e

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
        """Genereert een kindvriendelijk afleveringsscript inclusief motion_prompts voor animatie."""
        total_seconds = duration_minutes * 60
        target_scene_count = max(8, total_seconds // 12)
        char_str = ", ".join(characters) if characters else "Adam en Nora"

        system_prompt = (
            f"Je bent een top-scenarioschrijver voor educatieve kinderprogramma's zoals Sesamstraat en Cocomelon. "
            f"Doelgroep: kinderen van {target_age_min} tot {target_age_max} jaar oud. "
            f"Taal: Nederlands ({language}). "
            f"Pedagogische regels:\n"
            f"- Eenvoudige, ritmische, enthousiaste zinnen van maximaal 12 woorden.\n"
            f"- Interactief: stel regelmatig vragen aan de kijkertjes ('Zie jij de rode appel?').\n"
            f"- Absoluut GEEN enge of negatieve elementen.\n"
            f"- Verdeel het verhaal in circa {target_scene_count} opeenvolgende scènes van 8-15 seconden.\n"
            f"- Vul voor ELKE scène een actiegerichte Engelse motion_prompt in voor Image-to-Video AI (Google Veo/Wan)."
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
      "visual_prompt": "Gedetailleerde Engelse prompt voor AI Start-Frame image generator, vibrant colors, friendly style",
      "motion_prompt": "Engelse bewegingsopdracht voor Veo (bijv: Adam walks briskly towards the apple tree, jumps up with excitement, and points at a bright red apple while Nora claps happily. Smooth 2D cartoon animation)",
      "background_prompt": "Engelse beschrijving van de achtergrond omgeving zonder karakters",
      "animation_type": "ken_burns",
      "transition_type": "crossfade",
      "duration_seconds": 12.0,
      "pause_after_sec": 0.4
    }}
  ]
}}
"""
        raw_text = await self._generate_text(
            prompt=user_prompt,
            temperature=0.7,
            max_output_tokens=16384,
            json_mode=True,
            system_instruction=system_prompt,
        )

        parsed = json.loads(_clean_json_text(raw_text))
        if not isinstance(parsed.get("scenes"), list) or not parsed["scenes"]:
            raise RuntimeError("Gemini retourneerde geen geldige scènes in het script.")
        return parsed

    async def generate_seo(
        self,
        title: str = "",
        description: str = "",
        script: str = "",
        language: str = "nl",
    ) -> Dict[str, Any]:
        """Genereert geoptimaliseerde YouTube SEO metadata voor kindervideo's."""
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
  "thumbnail_prompt": "Engelse prompt voor een vrolijke, kleurrijke YouTube-thumbnail met de karakters"
}}
"""
        raw_text = await self._generate_text(
            prompt=prompt,
            temperature=0.5,
            max_output_tokens=4096,
            json_mode=True,
        )
        return json.loads(_clean_json_text(raw_text))

    async def generate_scene_motion_prompt(
        self,
        scene_description: str,
        narration: str = "",
        characters: Optional[List[str]] = None,
        animation_style: str = "vibrant character animation, lively cartoon actions, 60fps smooth",
    ) -> str:
        """Genereert een specifieke Engelse motion prompt voor Google Veo / Wan 2.1."""
        chars_text = ", ".join(characters) if characters else "characters"
        prompt = (
            f"Write a specific, cinematic English motion prompt for an Image-to-Video AI model (Google Veo / Wan 2.1).\n"
            f"The image already depicts the scene and characters. Describe ONLY how the characters and scene MOVE.\n"
            f"Characters in scene: {chars_text}\n"
            f"Scene Context: {scene_description}\n"
            f"Narration / Dialogue: {narration}\n"
            f"Style: {animation_style}\n"
            f"Requirements:\n"
            f"- Describe clear, lively actions: walking, jumping, pointing, smiling, nodding, waving, clapping.\n"
            f"- Make it energetic and suitable for a viral toddler/kids educational video.\n"
            f"- Max 2 sentences, pure English motion description without preamble or quotes."
        )
        return await self._generate_text(prompt=prompt, temperature=0.6, max_output_tokens=256)

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
        return await self._generate_text(prompt=prompt, temperature=0.4, max_output_tokens=512)

    # ─────────────────────────────────────────────────────────────
    # Echte Beeldgeneratie via Google Imagen / Gemini Multimodaal
    # ─────────────────────────────────────────────────────────────

    async def generate_image(
        self,
        prompt: str,
        reference_image_paths: Optional[List[str]] = None,
        aspect_ratio: str = "16:9",
        model: Optional[str] = None,
    ) -> bytes:
        """Genereert een echte afbeelding via Imagen of multimodale Gemini met referentieplaatjes."""
        client = self._get_client()
        selected_model = model or self._resolve_image_model()
        logger.info("Start Google Image generatie met model: %s", selected_model)

        # 1. Als referentie-afbeeldingen aanwezig zijn en het model multimodale input ondersteunt
        ref_images = []
        if reference_image_paths:
            for p in reference_image_paths:
                if p and os.path.exists(p) and os.path.getsize(p) > 0:
                    try:
                        ref_images.append(Image.open(p))
                    except Exception as e:
                        logger.warning("Kon referentie-afbeelding %s niet openen: %s", p, e)

        # 2. Multimodaal Gemini Image Model (als 'gemini' in de modelnaam zit of als referentiebeelden meegegeven zijn)
        if "gemini" in selected_model.lower():
            try:
                contents: List[Any] = []
                contents.extend(ref_images)
                contents.append(prompt)

                config = types.GenerateContentConfig(
                    response_modalities=["IMAGE", "TEXT"],
                )
                response = client.models.generate_content(
                    model=selected_model,
                    contents=contents,
                    config=config,
                )
                if response.candidates:
                    for part in response.candidates[0].content.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and getattr(inline_data, "data", None):
                            data = inline_data.data
                            if isinstance(data, str):
                                return base64.b64decode(data)
                            return data
                raise RuntimeError(
                    f"Gemini multimodaal model {selected_model} retourneerde geen afbeeldingsdata."
                )
            except Exception as e:
                # Als het specifieke gemini-image model niet actief is, probeer Imagen direct
                logger.warning("Gemini content image faalde (%s); probeer Imagen generator...", e)

        # 3. Imagen Generatie (client.models.generate_images)
        imagen_model = selected_model if "imagen" in selected_model.lower() else "imagen-3.0-generate-002"
        try:
            config = types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type="image/png",
                aspect_ratio=aspect_ratio,
                person_generation="ALLOW_ADULT",
            )
            result = client.models.generate_images(
                model=imagen_model,
                prompt=prompt,
                config=config,
            )
            if result.generated_images and len(result.generated_images) > 0:
                img_obj = result.generated_images[0].image
                if hasattr(img_obj, "image_bytes") and img_obj.image_bytes:
                    return img_obj.image_bytes
            raise RuntimeError(f"Google Imagen ({imagen_model}) retourneerde geen afbeeldingsbytes.")
        except Exception as e:
            logger.error("Google Imagen generatiefout (%s): %s", imagen_model, e)
            raise RuntimeError(f"Google Imagen Fout ({imagen_model}): {e}") from e

    async def generate_character_expression(
        self,
        character_name: str,
        visual_dna_prompt: str,
        emotion: str,
        reference_image_paths: Optional[List[str]] = None,
        style_prompt: str = "3D Pixar style cartoon hero, clean vibrant vector illustration",
    ) -> bytes:
        """Genereert een echte karakterillustratie met specifieke emotie en behoud van visueel DNA."""
        emotion_nl = emotion or "blij"
        prompt = (
            f"Full body standalone character illustration, character name: {character_name}. "
            f"Visual description & clothes: {visual_dna_prompt}. "
            f"Facial expression and pose: {emotion_nl}, expressive eyes, cheerful and engaging. "
            f"Style: {style_prompt}. "
            f"Strict requirements: Pure solid uniform white background, high contrast, clean outlines, "
            f"character is centered, full body visible from head to toe, no background scenery or props."
        )
        return await self.generate_image(
            prompt=prompt,
            reference_image_paths=reference_image_paths,
            aspect_ratio="1:1",
        )

    # ─────────────────────────────────────────────────────────────
    # Echte Google Veo Image-to-Video Animatie
    # ─────────────────────────────────────────────────────────────

    async def generate_video(
        self,
        prompt: str,
        image_path: str,
        model: Optional[str] = None,
        duration_seconds: int = 5,
    ) -> bytes:
        """Genereert een geanimeerde videoclip via de Google Veo API vanuit een Start-Frame."""
        import asyncio

        client = self._get_client()
        veo_model = model or self._resolve_video_model()

        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            raise ValueError(f"Start-Frame afbeelding niet gevonden: {image_path}")

        start_img = Image.open(image_path)
        logger.info("Start Google Veo video generatie via SDK (%s)...", veo_model)

        try:
            config = types.GenerateVideosConfig(
                aspect_ratio="16:9",
                number_of_videos=1,
                duration_seconds=duration_seconds,
                person_generation="ALLOW_ADULT",
            )
            operation = client.models.generate_videos(
                model=veo_model,
                prompt=prompt,
                image=start_img,
                config=config,
            )

            poll_count = 0
            while not operation.done and poll_count < 60:
                await asyncio.sleep(8)
                poll_count += 1
                operation = client.operations.get(operation)

            if not operation.done:
                raise TimeoutError(f"Google Veo ({veo_model}) generatie duurde langer dan 8 minuten.")

            result = operation.response
            if result and hasattr(result, "generated_videos") and len(result.generated_videos) > 0:
                video_obj = result.generated_videos[0].video
                if hasattr(video_obj, "video_bytes") and video_obj.video_bytes:
                    return video_obj.video_bytes
            raise RuntimeError(f"Google Veo ({veo_model}) heeft geen videobytes geretourneerd.")
        except Exception as e:
            logger.error("Google Veo API fout: %s", e)
            raise RuntimeError(f"Google Veo Fout ({veo_model}): {e}") from e


gemini_service = GeminiService()
