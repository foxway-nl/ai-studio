"""Video Animation Service – Echte Image-to-Video generatie (Google Veo, Wan 2.1 en Google Flow).

Implementeert het Start-Frame Lock -> Image-to-Video principe:
1. Google Veo 2.0 API (veo-2.0-generate-001) met Start-Frame lock
2. Wan 2.1 / Open-Source Image-to-Video API (Lokaal / Cloud API)
3. Gemini Pro Web / Google Flow Bulk Exporter (.zip met Start-Frames + Motion Prompts)
4. Handmatige Drag & Drop .mp4 clip upload en validatie
"""

import asyncio
import base64
import json
import logging
import os
import shutil
import time
import zipfile
from pathlib import Path
from typing import Any, Optional

import httpx
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_engine
from app.core.settings_manager import settings_manager
from app.models.models import Episode, Scene

logger = logging.getLogger(__name__)


def _to_media_url(path: Optional[str]) -> Optional[str]:
    """Zet een intern bestandspad om naar een veilige /api/media/... URL."""
    if not path:
        return None
    s = str(path).replace("\\", "/")
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/api/media/"):
        return s
    if s.startswith("/media/"):
        return f"/api{s}"
    if "/media/" in s:
        idx = s.index("/media/")
        return f"/api{s[idx:]}"
    return f"/api/media/{os.path.basename(s)}"


class VideoAnimationService:
    """Service voor het genereren, converteren en beheren van geanimeerde videoclips."""

    def __init__(self):
        settings.clips_dir.mkdir(parents=True, exist_ok=True)
        settings.exports_dir.mkdir(parents=True, exist_ok=True)

    def _get_gemini_key(self) -> str:
        key = settings_manager.get("gemini_api_key", settings.gemini_api_key) or ""
        return key.strip()

    def _get_wan_url(self) -> str:
        url = settings_manager.get("wan_api_url", settings.wan_api_url) or "http://host.docker.internal:8188"
        return url.strip().rstrip("/")

    def _get_wan_key(self) -> str:
        key = settings_manager.get("wan_api_key", settings.wan_api_key) or ""
        return key.strip()

    # ─────────────────────────────────────────────────────────────
    # Methode 1: Google Veo 2.0 Image-to-Video (veo-2.0-generate-001)
    # ─────────────────────────────────────────────────────────────

    async def generate_veo_video(
        self,
        image_path: str,
        motion_prompt: str,
        output_path: str,
        duration_seconds: int = 5,
    ) -> str:
        """Genereert een geanimeerde videoclip via Google Veo 2.0 met een Start-Frame."""
        api_key = self._get_gemini_key()
        if not api_key:
            raise ValueError(
                "Gemini API-sleutel ontbreekt. Vul deze eerst in via het Setup & Status Centrum."
            )

        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            raise ValueError(
                f"Start-Frame afbeelding niet gevonden op schijf: {image_path}. Genereer eerst het Start-Frame."
            )

        prompt = (motion_prompt or "").strip()
        if not prompt:
            prompt = "Smooth cinematic 2D cartoon animation, lively character movement, expressive actions."

        # Probeer eerst via google-genai SDK
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=api_key)

            with open(image_path, "rb") as f:
                image_bytes = f.read()

            mime = "image/png"
            if image_path.lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"

            logger.info("Start Google Veo 2.0 video generatie via SDK...")
            # Roep generate_videos aan met start-frame image lock
            operation = client.models.generate_videos(
                model="veo-2.0-generate-001",
                prompt=prompt,
                image=types.Image(image_bytes=image_bytes, mime_type=mime),
                config=types.GenerateVideosConfig(
                    aspect_ratio="16:9",
                    number_of_videos=1,
                    duration_seconds=duration_seconds,
                    person_generation="ALLOW_ADULT",
                ),
            )

            # Polling van de asynchrone bewerking
            poll_count = 0
            max_polls = 60  # tot 10 minuten
            while not operation.done and poll_count < max_polls:
                await asyncio.sleep(10)
                poll_count += 1
                operation = client.operations.get(operation)

            if not operation.done:
                raise TimeoutError("Veo 2.0 video generatie duurde langer dan 10 minuten.")

            # Download videobytes
            result = operation.result
            if hasattr(result, "generated_videos") and len(result.generated_videos) > 0:
                video_obj = result.generated_videos[0].video
                video_bytes = None
                if hasattr(video_obj, "video_bytes") and video_obj.video_bytes:
                    video_bytes = video_obj.video_bytes
                elif hasattr(video_obj, "uri") and video_obj.uri:
                    # Download vanaf URI
                    async with httpx.AsyncClient(timeout=60.0) as http_client:
                        resp = await http_client.get(f"{video_obj.uri}?key={api_key}")
                        if resp.status_code == 200:
                            video_bytes = resp.content

                if video_bytes:
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    with open(output_path, "wb") as f:
                        f.write(video_bytes)
                    logger.info("Veo 2.0 video succesvol opgeslagen in %s", output_path)
                    return output_path
                else:
                    raise RuntimeError("Geen videodata ontvangen van Veo 2.0 API.")
            else:
                raise RuntimeError("Veo 2.0 API heeft geen video's geretourneerd.")

        except ImportError:
            logger.info("google-genai SDK niet geladen, schakel over naar directe REST API...")
        except Exception as e:
            err_msg = str(e)
            logger.warning("Fout bij Veo via SDK: %s", err_msg)
            # Vang quota of billing meldingen specifiek af
            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg:
                raise RuntimeError(
                    "Google Veo Quota bereikt: je API-sleutel heeft de limiet bereikt of heeft Cloud Billing activatie nodig. Tip: gebruik optie 2 (Google Flow web export) voor gratis animaties via je Pro-abonnement."
                )
            if "403" in err_msg or "PERMISSION_DENIED" in err_msg:
                raise RuntimeError(
                    f"Google Veo toegang geweigerd (HTTP 403): {err_msg}. Controleer of de Veo API is ingeschakeld in je Google Cloud Project of gebruik Google Flow Web."
                )
            # Probeer fallback via REST API als de SDK faalde
            pass

        # Direct REST API Fallback voor Veo 2.0
        return await self._generate_veo_rest(api_key, image_path, prompt, output_path)

    async def _generate_veo_rest(
        self,
        api_key: str,
        image_path: str,
        prompt: str,
        output_path: str,
    ) -> str:
        """Directe REST API aanroep naar Google Generative Language API voor Veo 2.0."""
        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        mime = "image/png"
        if image_path.lower().endswith((".jpg", ".jpeg")):
            mime = "image/jpeg"

        url = f"https://generativelanguage.googleapis.com/v1beta/models/veo-2.0-generate-001:predictLongRunning?key={api_key}"
        payload = {
            "instances": [
                {
                    "prompt": prompt,
                    "image": {
                        "bytesBase64Encoded": b64_img,
                        "mimeType": mime,
                    },
                }
            ],
            "parameters": {
                "aspectRatio": "16:9",
                "sampleCount": 1,
                "durationSeconds": 5,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                err_text = resp.text
                if resp.status_code == 429:
                    raise RuntimeError(
                        "Google Veo API-quota bereikt (429). Gebruik Methode 2 (Exporteer voor Google Flow) om gratis animaties te genereren via je Google AI Pro browser-abonnement."
                    )
                if resp.status_code == 404:
                    raise RuntimeError(
                        "Veo 2.0 model nog niet direct actief op deze API-sleutel. Gebruik Methode 2 (Google Flow export) of Methode 3 (Wan 2.1)."
                    )
                raise RuntimeError(f"Google Veo REST API fout ({resp.status_code}): {err_text}")

            data = resp.json()
            operation_name = data.get("name")
            if not operation_name:
                raise RuntimeError("Geen operatie-ID ontvangen van Veo API.")

        # Poll operation
        poll_url = f"https://generativelanguage.googleapis.com/v1beta/{operation_name}?key={api_key}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            for _ in range(60):
                await asyncio.sleep(10)
                poll_resp = await client.get(poll_url)
                if poll_resp.status_code == 200:
                    poll_data = poll_resp.json()
                    if poll_data.get("done"):
                        response_data = poll_data.get("response", {})
                        videos = response_data.get("generatedVideos", [])
                        if videos and "video" in videos[0]:
                            video_info = videos[0]["video"]
                            video_uri = video_info.get("uri")
                            b64_bytes = video_info.get("bytesBase64Encoded")

                            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                            if b64_bytes:
                                with open(output_path, "wb") as f:
                                    f.write(base64.b64decode(b64_bytes))
                                return output_path
                            elif video_uri:
                                download_resp = await client.get(f"{video_uri}?key={api_key}")
                                if download_resp.status_code == 200:
                                    with open(output_path, "wb") as f:
                                        f.write(download_resp.content)
                                    return output_path
                        raise RuntimeError("Veo operatie gereed, maar geen geldige videodata.")

        raise TimeoutError("Veo REST API generatie duurde langer dan 10 minuten.")

    # ─────────────────────────────────────────────────────────────
    # Methode 2: Gemini Pro Web / Google Flow Bulk Export
    # ─────────────────────────────────────────────────────────────

    async def export_episode_flow(self, episode_id: str) -> dict[str, Any]:
        """Exporteert alle Start-Frames en Motion Prompts als een handige Google Flow / Gemini Web ZIP."""
        engine = get_engine()
        with Session(engine) as session:
            ep = session.get(Episode, episode_id)
            if not ep:
                raise ValueError(f"Aflevering {episode_id} niet gevonden.")

            stmt = (
                select(Scene)
                .where(Scene.episode_id == episode_id)
                .order_by(Scene.scene_number)
            )
            scenes = session.exec(stmt).all()

        if not scenes:
            raise ValueError("Deze aflevering bevat nog geen scènes om te exporteren.")

        zip_filename = f"flow_export_{episode_id}.zip"
        zip_path = settings.exports_dir / zip_filename
        zip_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "episode_id": episode_id,
            "episode_title": ep.title,
            "export_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "instructions": "Upload elk Start-Frame plaatje naar Google Flow / Gemini Web, plak de bijbehorende Motion Prompt, download de gegenereerde .mp4 en sleep deze direct terug in AI-Studio in de desbetreffende scène.",
            "scenes": [],
        }

        prompts_txt_lines = [
            f"=== GOOGLE FLOW / GEMINI WEB MOTION PROMPTS ===",
            f"Aflevering: {ep.title}",
            f"Instructie: Upload het start-plaatje en plak onderstaande Engelse motion prompt in Google Flow.",
            "=" * 60,
            "",
        ]

        # Bouw zip archief
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for sc in scenes:
                sc_num = sc.scene_number
                motion = (sc.motion_prompt or "").strip()
                if not motion:
                    motion = (
                        f"Smooth 2D cartoon animation: characters walk, talk and expressively gesture. "
                        f"Scene action: {sc.visual_prompt or sc.narration_text}"
                    )

                img_path = sc.composite_image_path or sc.background_image_path
                img_filename_in_zip = None

                if img_path and os.path.exists(img_path) and os.path.getsize(img_path) > 0:
                    ext = os.path.splitext(img_path)[1] or ".png"
                    img_filename_in_zip = f"frames/scene_{sc_num:02d}_start_frame{ext}"
                    zipf.write(img_path, arcname=img_filename_in_zip)

                scene_info = {
                    "scene_number": sc_num,
                    "scene_id": sc.id,
                    "title": sc.title or f"Scène {sc_num}",
                    "speaker": sc.speaker or "Verteller",
                    "narration": sc.narration_text,
                    "motion_prompt": motion,
                    "start_frame_file": img_filename_in_zip,
                }
                manifest["scenes"].append(scene_info)

                prompts_txt_lines.append(f"--- SCÈNE {sc_num:02d}: {sc.title or 'Scène ' + str(sc_num)} ---")
                prompts_txt_lines.append(f"Bestand Start-Frame: {img_filename_in_zip or 'NOG NIET GEGENEREERD'}")
                prompts_txt_lines.append(f"Gesproken Tekst: \"{sc.narration_text}\"")
                prompts_txt_lines.append(f"Motion Prompt voor Google Flow:")
                prompts_txt_lines.append(motion)
                prompts_txt_lines.append("")

            # Voeg README en manifest toe aan de zip
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False))
            zipf.writestr("prompts.txt", "\n".join(prompts_txt_lines))
            zipf.writestr(
                "INSTRUCTIES_NEDERLANDS.txt",
                (
                    "HOE TE GEBRUIKEN MET JE GOOGLE AI PRO ABONNEMENT:\n\n"
                    "1. Pak deze zip uit op je computer.\n"
                    "2. Open Google Flow of Gemini Web in je browser.\n"
                    "3. Per scène:\n"
                    "   a. Upload het bijbehorende plaatje uit de map 'frames/'.\n"
                    "   b. Kopieer en plak de 'Motion Prompt' uit prompts.txt.\n"
                    "   c. Klik op 'Generate Video' (Veo).\n"
                    "   d. Download de resulterende .mp4 video.\n"
                    "   e. Sleep het .mp4 bestand direct in AI-Studio in de desbetreffende scène!\n"
                    "4. AI-Studio synchroniseert de animatielengte automatisch met de gesproken audio!\n"
                ),
            )

        zip_url = _to_media_url(str(zip_path))
        return {
            "zip_path": str(zip_path),
            "zip_url": zip_url,
            "scene_count": len(scenes),
            "message": f"Google Flow export gereed met {len(scenes)} scènes.",
        }

    # ─────────────────────────────────────────────────────────────
    # Methode 3: Wan 2.1 / Open-Source Image-to-Video API
    # ─────────────────────────────────────────────────────────────

    async def generate_wan_video(
        self,
        image_path: str,
        motion_prompt: str,
        output_path: str,
    ) -> str:
        """Genereert animatie via een Wan 2.1 (ComfyUI / Fal.ai / Lokaal) endpoint."""
        wan_url = self._get_wan_url()
        wan_key = self._get_wan_key()

        if not os.path.exists(image_path) or os.path.getsize(image_path) == 0:
            raise ValueError(f"Start-Frame afbeelding niet gevonden: {image_path}")

        prompt = (motion_prompt or "").strip()
        if not prompt:
            prompt = "2D high quality cartoon character animation, smooth movements."

        with open(image_path, "rb") as f:
            b64_img = base64.b64encode(f.read()).decode("utf-8")

        headers = {"Content-Type": "application/json"}
        if wan_key:
            headers["Authorization"] = f"Bearer {wan_key}"

        # Standard Wan 2.1 payload compatibel met ComfyUI Wan wrapper of Fal.ai i2v
        payload = {
            "prompt": prompt,
            "image": f"data:image/png;base64,{b64_img}",
            "aspect_ratio": "16:9",
            "frames": 81,
            "fps": 16,
        }

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                resp = await client.post(f"{wan_url}/generate", json=payload, headers=headers)
                if resp.status_code == 200:
                    ct = resp.headers.get("content-type", "")
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    if "video/mp4" in ct:
                        with open(output_path, "wb") as f:
                            f.write(resp.content)
                        return output_path
                    else:
                        data = resp.json()
                        if "video_url" in data:
                            v_resp = await client.get(data["video_url"])
                            with open(output_path, "wb") as f:
                                f.write(v_resp.content)
                            return output_path
                        elif "video_base64" in data:
                            with open(output_path, "wb") as f:
                                f.write(base64.b64decode(data["video_base64"]))
                            return output_path

                raise RuntimeError(
                    f"Wan 2.1 API gaf HTTP {resp.status_code}: {resp.text[:300]}"
                )

        except httpx.ConnectError:
            raise RuntimeError(
                f"Wan 2.1 server is niet bereikbaar op {wan_url}. Controleer of je lokale ComfyUI/Wan container draait, of schakel over naar Google Veo / Google Flow export in het Setup Centrum."
            )

    # ─────────────────────────────────────────────────────────────
    # Handmatige Upload & Opslag van .mp4 videoclips
    # ─────────────────────────────────────────────────────────────

    async def save_uploaded_clip(
        self,
        scene_id: str,
        file_bytes: bytes,
        filename: str = "upload.mp4",
    ) -> tuple[str, str]:
        """Slaat een geüploade .mp4 videoclip op voor een scène."""
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Geüpload videobestand is leeg.")

        timestamp = int(time.time())
        dest_filename = f"scene_{scene_id}_{timestamp}.mp4"
        dest_path = settings.clips_dir / dest_filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        with open(dest_path, "wb") as f:
            f.write(file_bytes)

        url = _to_media_url(str(dest_path))
        logger.info("Video clip voor scène %s opgeslagen in %s (%s)", scene_id, dest_path, url)
        return str(dest_path), url or ""


video_animation_service = VideoAnimationService()

