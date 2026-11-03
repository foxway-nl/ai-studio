"""Afbeeldingengeneratie en 2.5D sprite compositing voor AI-Studio.

Echte AI-beeldgeneratie via:
- Google Imagen 3 / Gemini Multimodaal (Primaire engine via officiële google-genai SDK)
- Optioneel lokaal: Stable Diffusion WebUI Forge (/sdapi/v1/txt2img)
- Multi-karakter 2.5D compositie met transparante sprites en mond-animatie.
GEEN nep-placeholders, GEEN ImageDraw landschappen, GEEN verborgen fallbacks.
"""

import base64
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from PIL import Image, ImageDraw

from app.core.config import settings
from app.core.settings_manager import settings_manager
from app.services.gemini_service import gemini_service

logger = logging.getLogger(__name__)


def to_media_url(path: Optional[str]) -> Optional[str]:
    """Converteer elk intern bestandspad naar een gegarandeerde /api/media/... URL."""
    if not path:
        return None
    p = str(path).strip()
    if not p:
        return None
    if p.startswith("http://") or p.startswith("https://") or p.startswith("data:"):
        return p
    if p.startswith("/api/media/"):
        return p
    if p.startswith("/media/"):
        return "/api" + p
    if p.startswith("/data/media/"):
        return "/api/media/" + p[len("/data/media/"):]
    if p.startswith("/data/"):
        return "/api/media/" + p[len("/data/"):]
    return f"/api/media/{p.lstrip('/')}"


class ImageService:
    """Service voor echte AI-beeldgeneratie en 2.5D sprite compositie."""

    def __init__(self, sd_base_url: Optional[str] = None):
        self._custom_sd_url = sd_base_url
        settings.images_dir.mkdir(parents=True, exist_ok=True)
        settings.sprites_dir.mkdir(parents=True, exist_ok=True)
        settings.characters_dir.mkdir(parents=True, exist_ok=True)

    @property
    def sd_base_url(self) -> str:
        if self._custom_sd_url:
            return self._custom_sd_url.rstrip("/")
        url = settings_manager.get("sd_webui_base_url", settings.sd_webui_base_url)
        return url.rstrip("/") if url else "http://host.docker.internal:7860"

    async def generate_sdwebui(
        self,
        prompt: str,
        negative_prompt: str = "ugly, deformed, scary, violent, dark, text, watermark, bad anatomy",
        width: int = 1920,
        height: int = 1080,
        steps: int = 25,
        cfg_scale: float = 7.0,
        seed: int = -1,
    ) -> str:
        """Genereer een afbeelding via de lokale Stable Diffusion WebUI Forge REST API."""
        url = f"{self.sd_base_url}/sdapi/v1/txt2img"
        payload = {
            "prompt": f"{prompt}, vibrant colors, cute playful, 3d animation, child-friendly masterpiece",
            "negative_prompt": negative_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "sampler_name": "Euler a",
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code != 200:
                    raise RuntimeError(f"SD WebUI Forge fout ({resp.status_code}): {resp.text[:300]}")
                data = resp.json()
                images = data.get("images", [])
                if not images:
                    raise RuntimeError("Geen afbeelding ontvangen van SD WebUI Forge.")

                image_data = base64.b64decode(images[0])
                filename = f"sd_{uuid.uuid4().hex[:10]}.png"
                output_path = settings.images_dir / filename
                output_path.write_bytes(image_data)
                return str(output_path)
        except (httpx.ConnectError, httpx.ConnectTimeout):
            raise ConnectionError(
                "SD WebUI Forge draait momenteel niet op poort 7860. "
                "Start WebUI Forge lokaal op of schakel over naar 'Google Gemini / Imagen' in het Setup Centrum."
            )

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1920,
        height: int = 1080,
        provider: Optional[str] = None,
        reference_image_paths: Optional[List[str]] = None,
        aspect_ratio: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Centrale dispatcher voor echte beeldgeneratie (zonder mocks of nepplaatjes)."""
        configured_provider = settings_manager.get("default_image_provider", "gemini").lower()
        active_provider = (provider or configured_provider or "gemini").lower()

        # 1. SD WebUI Forge (alleen als expliciet gekozen)
        if active_provider in ("sdwebui", "forge", "local"):
            return await self.generate_sdwebui(
                prompt=prompt,
                negative_prompt=negative_prompt,
                width=width,
                height=height,
            )

        # 2. Google Gemini / Imagen 3 (Standaard officiële engine)
        ar = aspect_ratio or ("16:9" if width >= height else "1:1")
        img_bytes = await gemini_service.generate_image(
            prompt=prompt,
            reference_image_paths=reference_image_paths,
            aspect_ratio=ar,
            model=model,
        )

        filename = f"gen_{uuid.uuid4().hex[:10]}.png"
        output_path = settings.images_dir / filename
        output_path.write_bytes(img_bytes)

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Gegenereerde afbeelding kon niet worden opgeslagen op schijf.")

        return str(output_path)

    async def generate_character_sprite(
        self,
        character_id: str,
        character_name: str = "Karakter",
        visual_dna_prompt: str = "",
        emotion: str = "blij",
        reference_image_paths: Optional[List[str]] = None,
        style_prompt: str = "3D Pixar style cute cartoon hero, vibrant saturated colors",
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Genereert een echte AI-karakterillustratie via Google Imagen/Gemini met transparantie.
        
        Gebruikt het visueel DNA en eventuele referentie-afbeeldingen van het karakter
        om het uiterlijk strikt consistent te houden.
        """
        dest_dir = Path(output_dir) if output_dir else settings.characters_dir / character_id
        dest_dir.mkdir(parents=True, exist_ok=True)
        settings.sprites_dir.mkdir(parents=True, exist_ok=True)

        emotion_nl = emotion or "blij"
        dna = (visual_dna_prompt or "").strip()
        if not dna:
            dna = f"Cute 5-year-old child cartoon character named {character_name}, expressive friendly face, colorful clothes"

        logger.info("Genereer echte AI sprite voor '%s' (emotie: %s)...", character_name, emotion_nl)

        # Roep Gemini/Imagen aan voor echte AI illustratie
        img_bytes = await gemini_service.generate_character_expression(
            character_name=character_name,
            visual_dna_prompt=dna,
            emotion=emotion_nl,
            reference_image_paths=reference_image_paths,
            style_prompt=style_prompt,
        )

        raw_path = dest_dir / f"raw_{emotion_nl}_{uuid.uuid4().hex[:6]}.png"
        raw_path.write_bytes(img_bytes)

        # Laad en converteer naar transparante PNG (verwijder effen witte/zeer lichte achtergrond)
        orig = Image.open(raw_path).convert("RGBA")
        datas = orig.getdata()
        new_data = []
        for item in datas:
            # Als pixel bijna zuiver wit is (> 235 op RGB) -> maak transparant
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        orig.putdata(new_data)

        # Sla opgeschoonde transparante sprite op
        sprite_filename = f"sprite_{emotion_nl}_{uuid.uuid4().hex[:6]}.png"
        sprite_file = dest_dir / sprite_filename
        orig.save(str(sprite_file), "PNG")

        # Ook in centrale sprites map
        central_sprite = settings.sprites_dir / sprite_filename
        orig.save(str(central_sprite), "PNG")

        # Genereer mond-sprites voor pratende animatie
        mouth_open = self._create_mouth_sprite(dest_dir, is_open=True, emotion=emotion_nl)
        mouth_closed = self._create_mouth_sprite(dest_dir, is_open=False, emotion=emotion_nl)

        self._create_mouth_sprite(settings.sprites_dir, is_open=True, emotion=emotion_nl)
        self._create_mouth_sprite(settings.sprites_dir, is_open=False, emotion=emotion_nl)

        return {
            "sprite_path": str(sprite_file),
            "sprite_url": to_media_url(str(sprite_file)),
            "mouth_open_path": str(mouth_open),
            "mouth_open_url": to_media_url(str(mouth_open)),
            "mouth_closed_path": str(mouth_closed),
            "mouth_closed_url": to_media_url(str(mouth_closed)),
            "emotion": emotion_nl,
        }

    def _create_mouth_sprite(self, target_dir: Path, is_open: bool, emotion: str) -> Path:
        """Genereert een transparante mond-overlay voor lip-sync animatie."""
        size = (200, 200)
        img = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        lip_color = (220, 60, 80, 255)
        tongue_color = (255, 120, 140, 255)
        inside_mouth = (120, 20, 35, 255)
        teeth_color = (255, 255, 255, 255)

        if is_open:
            draw.pieslice([40, 60, 160, 150], 0, 180, fill=inside_mouth, outline=lip_color, width=4)
            draw.rectangle([65, 105, 135, 115], fill=teeth_color)
            draw.pieslice([70, 115, 130, 150], 0, 180, fill=tongue_color)
            draw.arc([40, 95, 160, 115], 180, 360, fill=lip_color, width=5)
            filename = f"mouth_open_{emotion}.png"
        else:
            draw.arc([45, 80, 155, 140], 20, 160, fill=lip_color, width=6)
            draw.line([45, 95, 52, 90], fill=lip_color, width=4)
            draw.line([155, 95, 148, 90], fill=lip_color, width=4)
            filename = f"mouth_closed_{emotion}.png"

        target_file = target_dir / filename
        img.save(str(target_file), "PNG")
        return target_file

    def composite_2_5d_scene(
        self,
        background_path: str,
        characters: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> str:
        """Plaats meerdere karakter-sprites met transparantie op de achtergrond."""
        if not os.path.exists(background_path):
            raise FileNotFoundError(f"Achtergrondbestand niet gevonden: {background_path}")

        bg = Image.open(background_path).convert("RGBA").resize((1920, 1080))

        # Posities op het 1920x1080 canvas
        pos_map = {
            "left": (180, 220),
            "center": (680, 220),
            "right": (1180, 220),
            "far_left": (50, 240),
            "far_right": (1320, 240),
        }

        for char in characters:
            sprite_path = char.get("sprite_path")
            if not sprite_path or not os.path.exists(sprite_path):
                continue

            try:
                sprite = Image.open(sprite_path).convert("RGBA")
                scale = float(char.get("scale", 0.65))
                w = int(sprite.width * scale)
                h = int(sprite.height * scale)
                if w > 0 and h > 0:
                    sprite = sprite.resize((w, h), Image.Resampling.LANCZOS)

                slot = char.get("position", "center")
                x, y = pos_map.get(slot, (680, 220))
                offset_x = int(char.get("offset_x", 0))
                offset_y = int(char.get("offset_y", 0))

                final_x = max(0, min(1920 - w, x + offset_x))
                final_y = max(0, min(1080 - h, y + offset_y))

                bg.paste(sprite, (final_x, final_y), sprite)
            except Exception as e:
                logger.warning("Fout bij compositing van sprite %s: %s", sprite_path, e)

        dest = output_path or str(settings.images_dir / f"composite_{uuid.uuid4().hex[:8]}.png")
        bg.convert("RGB").save(dest, "PNG", quality=95)
        return dest


image_service = ImageService()
