"""Afbeeldingengeneratie en 2.5D sprite compositing voor AI-Studio.

Ondersteunt Stable Diffusion WebUI Forge (REST API /sdapi/v1/txt2img),
Google Imagen 3 via Gemini, en compositie van gelaagde 2.5D kinderanimatie-scènes
met Pillow.
"""

import base64
import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class ImageService:
    """Service voor AI-beeldgeneratie en 2.5D sprite compositie."""

    def __init__(self, sd_base_url: Optional[str] = None):
        self._custom_sd_url = sd_base_url

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
        """Genereer een afbeelding via de Stable Diffusion WebUI Forge API."""
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

        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"SD WebUI fout ({resp.status_code}): {resp.text}")
            data = resp.json()
            images = data.get("images", [])
            if not images:
                raise RuntimeError("Geen afbeelding ontvangen van SD WebUI")

            image_data = base64.b64decode(images[0])
            filename = f"sd_{uuid.uuid4().hex[:10]}.png"
            output_path = settings.images_dir / filename
            output_path.write_bytes(image_data)
            return str(output_path)

    async def generate_imagen(
        self,
        prompt: str,
        width: int = 1920,
        height: int = 1080,
    ) -> str:
        """Genereer een afbeelding via Google Imagen 3."""
        from app.services.gemini_service import gemini_service

        img_bytes = await gemini_service.generate_with_imagen(prompt, width=width, height=height)
        filename = f"imagen_{uuid.uuid4().hex[:10]}.png"
        output_path = settings.images_dir / filename
        output_path.write_bytes(img_bytes)
        return str(output_path)

    def _create_placeholder_image(self, prompt: str, width: int = 1920, height: int = 1080) -> str:
        """Maak een mooie grafische kindvriendelijke vector-achtige achtergrond als noodoplossing."""
        img = Image.new("RGB", (width, height), color=(135, 206, 235))  # Hemelsblauw
        draw = ImageDraw.Draw(img)

        # Zonnetje
        draw.ellipse([width - 300, 50, width - 100, 250], fill=(255, 223, 0), outline=(255, 180, 0), width=4)

        # Glooiende groene heuvels
        draw.chord([-200, height // 2, width // 2 + 200, height + 400], 180, 360, fill=(76, 175, 80))
        draw.chord([width // 3, height // 2 - 50, width + 400, height + 500], 180, 360, fill=(129, 199, 132))

        filename = f"scene_{uuid.uuid4().hex[:8]}.png"
        out_path = settings.images_dir / filename
        img.save(str(out_path), quality=95)
        return str(out_path)

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1920,
        height: int = 1080,
        provider: str = "sdwebui",
        style: str = "kids_illustration",
    ) -> str:
        """Centrale dispatcher voor afbeeldinggeneratie."""
        provider_norm = (provider or "sdwebui").lower()

        if provider_norm in ("imagen", "gemini"):
            try:
                return await self.generate_imagen(prompt=prompt, width=width, height=height)
            except Exception as e:
                logger.warning("Imagen faalde (%s), val terug op SD WebUI of lokaal canvas.", e)

        # SD WebUI
        try:
            return await self.generate_sdwebui(
                prompt=f"{prompt}, {style}",
                negative_prompt=negative_prompt,
                width=width,
                height=height,
            )
        except Exception as e:
            logger.warning("SD WebUI niet beschikbaar (%s), genereer canvas render.", e)
            return self._create_placeholder_image(prompt=prompt, width=width, height=height)

    def composite_2_5d_scene(
        self,
        background_path: str,
        characters: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> str:
        """Plaats karakter-sprites met transparantie op de achtergrond.

        characters structuur:
        [
            {
                "sprite_path": "/path/to/sprite.png",
                "x_percent": 0.5,    # 0.0 (links) - 1.0 (rechts)
                "y_percent": 0.7,    # 0.0 (boven) - 1.0 (onder)
                "scale": 1.0,        # Relatieve schaal
                "flip_horizontal": False
            }
        ]
        """
        if not output_path:
            out_file = settings.images_dir / f"comp_{uuid.uuid4().hex[:10]}.png"
            output_path = str(out_file)

        bg_file = Path(background_path)
        if not bg_file.exists():
            bg_path = self._create_placeholder_image("vrolijke speelplaats")
            bg = Image.open(bg_path).convert("RGBA")
        else:
            bg = Image.open(str(bg_file)).convert("RGBA")

        bg_w, bg_h = bg.size

        for char in characters:
            sprite_path = char.get("sprite_path")
            if not sprite_path or not os.path.exists(sprite_path):
                continue

            sprite = Image.open(sprite_path).convert("RGBA")

            if char.get("flip_horizontal"):
                sprite = ImageOps.mirror(sprite)

            scale = float(char.get("scale", 1.0))
            # Schaal karakter passend bij 1080p resolutie (standaard ca 40% van schermhoogte)
            target_h = int(bg_h * 0.45 * scale)
            aspect = sprite.width / max(1, sprite.height)
            target_w = int(target_h * aspect)

            sprite_resized = sprite.resize((max(10, target_w), max(10, target_h)), Image.Resampling.LANCZOS)

            x_pct = float(char.get("x_percent", 0.5))
            y_pct = float(char.get("y_percent", 0.7))

            # Plaatsing gecentreerd op sprite voetjes
            pos_x = int(bg_w * x_pct - (target_w // 2))
            pos_y = int(bg_h * y_pct - target_h)

            # Plak sprite met alpha masker
            bg.paste(sprite_resized, (pos_x, pos_y), sprite_resized)

        final_rgb = bg.convert("RGB")
        final_rgb.save(output_path, "PNG", quality=95)
        return output_path

    async def generate_character_sprite(
        self,
        description: str,
        style_prompt: str = "3d Pixar character sprite, friendly big eyes",
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """Genereer een vrolijke karaktersprite met transparante achtergrond."""
        prompt = (
            f"Full body character cutout, {description}, {style_prompt}, "
            f"pure solid white background, cute friendly child-appropriate cartoon hero"
        )
        img_path = await self.generate_image(prompt, width=1024, height=1024)

        # Verwijder witte achtergrond naar transparante RGBA
        dest_dir = Path(output_dir) if output_dir else settings.characters_dir
        dest_dir.mkdir(parents=True, exist_ok=True)

        orig = Image.open(img_path).convert("RGBA")
        datas = orig.getdata()
        new_data = []
        for item in datas:
            # Als pixel zeer licht/wit is, maak transparant
            if item[0] > 240 and item[1] > 240 and item[2] > 240:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        orig.putdata(new_data)

        sprite_file = dest_dir / "sprite_base.png"
        orig.save(str(sprite_file), "PNG")

        return {"sprite_path": str(sprite_file)}


image_service = ImageService()

