"""Afbeeldingengeneratie en 2.5D sprite compositing voor AI-Studio.

Ondersteunt:
- Google Gemini / Imagen 3 (Primaire cloud engine)
- Ingebouwde Cloud Generator (Pollinations Flux API – gratis, sleutelloos)
- Stable Diffusion WebUI Forge (REST API /sdapi/v1/txt2img op poort 7860)
- Multi-karakter 2.5D Sprite compositie en automatische mond-sprite generatie met Pillow.
"""

import base64
import json
import logging
import os
import urllib.parse
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


def to_media_url(path: Optional[str]) -> Optional[str]:
    """Converteer elk bestandspad naar een gegarandeerde /api/media/... URL."""
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
    """Service voor AI-beeldgeneratie en 2.5D sprite compositie."""

    def __init__(self, sd_base_url: Optional[str] = None):
        self._custom_sd_url = sd_base_url

    @property
    def sd_base_url(self) -> str:
        if self._custom_sd_url:
            return self._custom_sd_url.rstrip("/")
        url = settings_manager.get("sd_webui_base_url", settings.sd_webui_base_url)
        return url.rstrip("/") if url else "http://host.docker.internal:7860"

    async def generate_pollinations(
        self,
        prompt: str,
        width: int = 1920,
        height: int = 1080,
        seed: int = -1,
    ) -> str:
        """Genereer een afbeelding via de gratis, sleutelloze Pollinations Flux API.
        
        Werkt altijd als betrouwbare cloud fallback zonder API-sleutel.
        """
        clean_prompt = urllib.parse.quote(prompt[:400])
        seed_param = f"&seed={seed}" if seed > 0 else ""
        url = (
            f"https://image.pollinations.ai/prompt/{clean_prompt}"
            f"?width={width}&height={height}&model=flux&nologo=true{seed_param}"
        )

        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Pollinations Flux fout ({resp.status_code}): {resp.text[:200]}"
                )
            if len(resp.content) < 500:
                raise RuntimeError("Pollinations retourneerde een te klein of ongeldig bestand.")

            filename = f"flux_{uuid.uuid4().hex[:10]}.png"
            output_path = settings.images_dir / filename
            output_path.write_bytes(resp.content)

            if not output_path.exists() or output_path.stat().st_size == 0:
                raise RuntimeError("Pollinations bestand kon niet worden opgeslagen op schijf.")

            return str(output_path)

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
        """Genereer een afbeelding via de Stable Diffusion WebUI Forge REST API."""
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
                    raise RuntimeError(f"SD WebUI fout ({resp.status_code}): {resp.text[:300]}")
                data = resp.json()
                images = data.get("images", [])
                if not images:
                    raise RuntimeError("Geen afbeelding ontvangen van SD WebUI")

                image_data = base64.b64decode(images[0])
                filename = f"sd_{uuid.uuid4().hex[:10]}.png"
                output_path = settings.images_dir / filename
                output_path.write_bytes(image_data)
                return str(output_path)
        except (httpx.ConnectError, httpx.ConnectTimeout) as ce:
            logger.warning("SD WebUI Forge niet bereikbaar op %s: %s", self.sd_base_url, ce)
            raise ConnectionError(
                "SD WebUI Forge draait momenteel niet op poort 7860. "
                "Schakel over naar 'Google Gemini / Imagen' of 'Ingebouwde Cloud Generator' als je Forge niet lokaal gebruikt."
            )

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

        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Imagen bestand kon niet worden opgeslagen op schijf.")

        return str(output_path)

    def _create_placeholder_image(self, prompt: str, width: int = 1920, height: int = 1080) -> str:
        """Maak een mooie grafische kindvriendelijke vector-achtige achtergrond als uiterste noodoplossing."""
        img = Image.new("RGB", (width, height), color=(135, 206, 235))  # Hemelsblauw
        draw = ImageDraw.Draw(img)

        # Zonnetje
        draw.ellipse([width - 300, 50, width - 100, 250], fill=(255, 223, 0), outline=(255, 180, 0), width=4)

        # Glooiende groene heuvels
        draw.chord([-200, height // 2, width // 2 + 200, height + 400], 180, 360, fill=(76, 175, 80))
        draw.chord([width // 3, height // 2 - 50, width + 400, height + 500], 180, 360, fill=(129, 199, 132))

        # Een paar vrolijke wolkjes
        for wx, wy in [(200, 100), (500, 80), (1200, 120)]:
            draw.ellipse([wx, wy, wx + 120, wy + 60], fill=(255, 255, 255, 230))
            draw.ellipse([wx + 40, wy - 20, wx + 160, wy + 60], fill=(255, 255, 255, 230))
            draw.ellipse([wx + 100, wy, wx + 200, wy + 60], fill=(255, 255, 255, 230))

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
        provider: Optional[str] = None,
        style: str = "kids_illustration",
    ) -> str:
        """Centrale dispatcher voor afbeeldinggeneratie met intelligente cascading fallback.
        
        Volgorde:
        1. Als provider expliciet is ingesteld op SD WebUI: probeer SD WebUI Forge.
        2. Anders (standaard): Google Gemini / Imagen 3 als er een sleutel is.
        3. Fallback naar Pollinations Flux API (sleutelloos, snel, gratis).
        4. Noodoplossing naar Pillow grafisch canvas (nooit crashen).
        """
        # Bepaal gewenste provider uit argument of settings
        configured_provider = settings_manager.get("default_image_provider", "gemini").lower()
        active_provider = (provider or configured_provider or "gemini").lower()

        # 1. SD WebUI Forge (alleen als specifiek gevraagd)
        if active_provider in ("sdwebui", "forge", "local"):
            try:
                return await self.generate_sdwebui(
                    prompt=f"{prompt}, {style}",
                    negative_prompt=negative_prompt,
                    width=width,
                    height=height,
                )
            except ConnectionError as ce:
                logger.warning("SD Forge niet bereikbaar (%s); val terug op Gemini / Cloud generator.", ce)
                # Ga door naar cloud engines

        # 2. Google Gemini / Imagen 3 (Primaire Cloud Engine)
        gemini_key = settings_manager.get("gemini_api_key", settings.gemini_api_key)
        if gemini_key and gemini_key.strip():
            try:
                return await self.generate_imagen(prompt=prompt, width=width, height=height)
            except Exception as e:
                logger.warning("Imagen 3 generatie faalde (%s); val terug op Pollinations Flux API.", e)

        # 3. Pollinations Flux API (Gratis, Zero-Config Cloud Fallback)
        try:
            return await self.generate_pollinations(
                prompt=f"{prompt}, 3d vibrant cute animation Pixar style, cheerful colors",
                width=width,
                height=height,
            )
        except Exception as e:
            logger.warning("Pollinations Flux API faalde (%s); genereer canvas achtergrond.", e)

        # 4. Lokale Pillow canvas fallback
        return self._create_placeholder_image(prompt=prompt, width=width, height=height)

    def composite_2_5d_scene(
        self,
        background_path: str,
        characters: List[Dict[str, Any]],
        output_path: Optional[str] = None,
    ) -> str:
        """Plaats meerdere karakter-sprites met transparantie op de achtergrond.

        characters structuur:
        [
            {
                "sprite_path": "/path/to/sprite.png",
                "position": "left" | "center" | "right",  # of x_percent
                "x_percent": 0.25,
                "y_percent": 0.88,
                "scale": 1.0,
                "flip_horizontal": False,
                "emotion": "blij"
            }
        ]
        """
        if not output_path:
            out_file = settings.images_dir / f"comp_{uuid.uuid4().hex[:10]}.png"
            output_path = str(out_file)

        bg_file = Path(background_path) if background_path else None
        if not bg_file or not bg_file.exists() or bg_file.stat().st_size == 0:
            bg_path = self._create_placeholder_image("vrolijke speelplaats")
            bg = Image.open(bg_path).convert("RGBA")
        else:
            bg = Image.open(str(bg_file)).convert("RGBA")

        bg_w, bg_h = bg.size

        # Positie mappings
        pos_map = {
            "left": 0.25,
            "links": 0.25,
            "center": 0.50,
            "midden": 0.50,
            "right": 0.75,
            "rechts": 0.75,
        }

        for char in characters:
            sprite_path = char.get("sprite_path")
            if not sprite_path or not os.path.exists(sprite_path) or os.path.getsize(sprite_path) == 0:
                continue

            try:
                sprite = Image.open(sprite_path).convert("RGBA")
            except Exception as exc:
                logger.warning("Kon sprite %s niet inladen: %s", sprite_path, exc)
                continue

            if char.get("flip_horizontal"):
                sprite = ImageOps.mirror(sprite)

            scale = float(char.get("scale", 1.0))
            # Schaal karakter passend bij 1080p resolutie (standaard ca 45% van schermhoogte)
            target_h = int(bg_h * 0.45 * scale)
            aspect = sprite.width / max(1, sprite.height)
            target_w = int(target_h * aspect)

            sprite_resized = sprite.resize(
                (max(10, target_w), max(10, target_h)),
                Image.Resampling.LANCZOS,
            )

            # Positiebepaling
            pos_key = str(char.get("position", "")).lower()
            default_x = pos_map.get(pos_key, float(char.get("x_percent", 0.5)))
            x_pct = default_x
            y_pct = float(char.get("y_percent", 0.88))

            # Plaatsing gecentreerd op voetjes van de sprite
            pos_x = int(bg_w * x_pct - (target_w // 2))
            pos_y = int(bg_h * y_pct - target_h)

            # Veilig klemmen binnen canvas grenzen
            pos_x = max(0, min(bg_w - target_w, pos_x))
            pos_y = max(0, min(bg_h - target_h, pos_y))

            # Plak sprite met alpha masker
            bg.paste(sprite_resized, (pos_x, pos_y), sprite_resized)

        final_rgb = bg.convert("RGB")
        final_rgb.save(output_path, "PNG", quality=95)
        return output_path

    async def generate_character_sprite(
        self,
        description: str,
        emotion: str = "blij",
        style_prompt: str = "3d Pixar character sprite, friendly big eyes",
        output_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Genereer een vrolijke karaktersprite met transparante achtergrond en mond-sprites.

        Maakt:
        - sprite_base.png (volledig karakter op transparante achtergrond)
        - mouth_open.png (open mondje t.b.v. spraak lip-sync)
        - mouth_closed.png (gesloten vrolijk mondje)
        Alle bestanden worden gevalideerd op schijf (> 0 bytes).
        """
        emotion_nl = emotion or "blij"
        prompt = (
            f"Full body standalone character cutout, {description}, emotion: {emotion_nl}, "
            f"{style_prompt}, pure solid uniform white background, cute friendly child-appropriate "
            f"cartoon hero, high contrast, vibrant colors, isolated"
        )

        img_path = await self.generate_image(prompt, width=1024, height=1024)

        dest_dir = Path(output_dir) if output_dir else settings.characters_dir
        dest_dir.mkdir(parents=True, exist_ok=True)
        settings.sprites_dir.mkdir(parents=True, exist_ok=True)

        orig = Image.open(img_path).convert("RGBA")

        # 1. Verwijder witte/zeer lichte achtergrond naar transparante RGBA
        datas = orig.getdata()
        new_data = []
        for item in datas:
            if item[0] > 235 and item[1] > 235 and item[2] > 235:
                new_data.append((255, 255, 255, 0))
            else:
                new_data.append(item)
        orig.putdata(new_data)

        # Sla basis sprite op
        sprite_filename = f"sprite_{emotion_nl}_{uuid.uuid4().hex[:6]}.png"
        sprite_file = dest_dir / sprite_filename
        orig.save(str(sprite_file), "PNG")

        # Ook opslaan in centrale sprites directory
        central_sprite_file = settings.sprites_dir / sprite_filename
        orig.save(str(central_sprite_file), "PNG")

        # 2. Genereer mouth_open.png en mouth_closed.png mond-sprites
        # We maken twee nette, transparante 256x256 mond-sprites die over het gezicht gepositioneerd kunnen worden
        mouth_open_path = self._create_mouth_sprite(dest_dir, is_open=True, emotion=emotion_nl)
        mouth_closed_path = self._create_mouth_sprite(dest_dir, is_open=False, emotion=emotion_nl)

        # Ook in centrale sprites directory
        self._create_mouth_sprite(settings.sprites_dir, is_open=True, emotion=emotion_nl)
        self._create_mouth_sprite(settings.sprites_dir, is_open=False, emotion=emotion_nl)

        return {
            "sprite_path": str(sprite_file),
            "sprite_url": to_media_url(str(sprite_file)),
            "mouth_open_path": str(mouth_open_path),
            "mouth_open_url": to_media_url(str(mouth_open_path)),
            "mouth_closed_path": str(mouth_closed_path),
            "mouth_closed_url": to_media_url(str(mouth_closed_path)),
            "emotion": emotion_nl,
        }

    def _create_mouth_sprite(self, target_dir: Path, is_open: bool, emotion: str) -> Path:
        """Genereer een vrolijke, transparante cartoon mond-sprite voor lip-sync."""
        size = (200, 200)
        img = Image.new("RGBA", size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(img)

        # Cartoon lippenkleur
        lip_color = (220, 60, 80, 255)
        tongue_color = (255, 120, 140, 255)
        inside_mouth = (120, 20, 35, 255)
        teeth_color = (255, 255, 255, 255)

        if is_open:
            # Open pratende mond
            # Mondholte
            draw.pieslice([40, 60, 160, 150], 0, 180, fill=inside_mouth, outline=lip_color, width=4)
            # Tanden boven
            draw.rectangle([65, 105, 135, 115], fill=teeth_color)
            # Tong
            draw.pieslice([70, 115, 130, 150], 0, 180, fill=tongue_color)
            # Bovenlip boog
            draw.arc([40, 95, 160, 115], 180, 360, fill=lip_color, width=5)
            filename = f"mouth_open_{emotion}.png"
        else:
            # Vriendelijke gesloten glimlach
            draw.arc([45, 80, 155, 140], 20, 160, fill=lip_color, width=6)
            # Kuiltjes aan de zijkanten
            draw.line([45, 95, 52, 90], fill=lip_color, width=4)
            draw.line([155, 95, 148, 90], fill=lip_color, width=4)
            filename = f"mouth_closed_{emotion}.png"

        target_file = target_dir / filename
        img.save(str(target_file), "PNG")
        return target_file


image_service = ImageService()
