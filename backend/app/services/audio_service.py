"""Audio & Text-to-Speech service voor AI-Studio.

Ondersteunt:
- Microsoft Edge TTS (Gratis, zero-config, hoogwaardige kinder- en vertelstemmen zoals Fenna en Maarten)
- Google Cloud TTS (WaveNet stemmen via Gemini sleutel)
- Piper TTS (lokaal/snel .onnx)
- Kokoro TTS (high quality REST)
- faster-whisper analyse voor exacte woord-level timestamps t.b.v. lip-sync animaties.
"""

import asyncio
import json
import logging
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import soundfile as sf

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)

# Beschikbare stemmen per provider
AVAILABLE_VOICES = {
    "edge_tts": [
        {
            "id": "nl-NL-FennaNeural",
            "name": "Fenna (Nederlands - Vrolijk & Helder, ideaal voor peuters/kleuters)",
            "gender": "female",
            "language": "nl-NL",
            "recommended": True,
        },
        {
            "id": "nl-NL-MaartenNeural",
            "name": "Maarten (Nederlands - Warm, vriendelijk & enthousiast)",
            "gender": "male",
            "language": "nl-NL",
            "recommended": True,
        },
        {
            "id": "nl-BE-DenaNeural",
            "name": "Dena (Vlaams - Zacht & liefdevol)",
            "gender": "female",
            "language": "nl-BE",
            "recommended": False,
        },
        {
            "id": "en-US-AnaNeural",
            "name": "Ana (Engels - Kindvriendelijke kinderstem)",
            "gender": "female",
            "language": "en-US",
            "recommended": False,
        },
    ],
    "google": [
        {
            "id": "nl-NL-Wavenet-A",
            "name": "Google WaveNet Vrouw (nl-NL)",
            "gender": "female",
            "language": "nl-NL",
            "recommended": False,
        },
        {
            "id": "nl-NL-Wavenet-B",
            "name": "Google WaveNet Man (nl-NL)",
            "gender": "male",
            "language": "nl-NL",
            "recommended": False,
        },
        {
            "id": "nl-NL-Standard-A",
            "name": "Google Standaard Vrouw (nl-NL)",
            "gender": "female",
            "language": "nl-NL",
            "recommended": False,
        },
    ],
    "piper": [
        {
            "id": "nl_NL-mls-medium",
            "name": "Piper MLS Medium (Lokaal ONNX)",
            "gender": "female",
            "language": "nl-NL",
            "recommended": False,
        },
        {
            "id": "nl_BE-nathalie-medium",
            "name": "Piper Nathalie (Vlaams ONNX)",
            "gender": "female",
            "language": "nl-BE",
            "recommended": False,
        },
    ],
    "kokoro": [
        {
            "id": "af_bella",
            "name": "Kokoro Bella (High-Quality)",
            "gender": "female",
            "language": "en/nl",
            "recommended": False,
        },
        {
            "id": "am_adam",
            "name": "Kokoro Adam (Warm Male)",
            "gender": "male",
            "language": "en/nl",
            "recommended": False,
        },
    ],
}


class AudioService:
    """Service voor spraaksynthese en audioverwerking."""

    def __init__(self):
        self._whisper_model = None

    def get_available_voices(self) -> Dict[str, List[Dict[str, Any]]]:
        """Haal de geconfigureerde stemmenlijst op."""
        return AVAILABLE_VOICES

    def _get_whisper_model(self):
        """Lazy load faster-whisper model om geheugen te sparen."""
        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel

                # Gebruik tiny of base model op CPU met INT8 quantisatie
                self._whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
            except Exception as e:
                logger.warning("Kon faster-whisper niet laden: %s", e)
                return None
        return self._whisper_model

    def get_audio_duration(self, audio_path: str) -> float:
        """Haal de exacte duur van een audiobestand op in seconden."""
        p = Path(audio_path)
        if not p.exists() or p.stat().st_size == 0:
            return 0.0
        try:
            with sf.SoundFile(str(p)) as f:
                return float(len(f)) / float(f.samplerate)
        except Exception as e:
            logger.debug("Soundfile duur controle faalde (%s), probeer ffprobe.", e)
            try:
                import subprocess

                cmd = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    str(p),
                ]
                output = subprocess.check_output(cmd).decode().strip()
                return float(output)
            except Exception:
                return 0.0

    async def generate_tts_edge(
        self,
        text: str,
        voice_id: str = "nl-NL-FennaNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        output_path: Optional[str] = None,
    ) -> str:
        """Genereer hoogwaardige spraak via de gratis Microsoft Edge TTS service.
        
        Ideaal voor Nederlandse kinderstemmen zonder API kosten.
        """
        import edge_tts

        if not output_path:
            out_file = settings.audio_dir / f"edge_{uuid.uuid4().hex[:10]}.mp3"
            output_path = str(out_file)

        voice = voice_id or "nl-NL-FennaNeural"
        clean_rate = rate if rate and ("%" in rate or "Hz" in rate) else "+0%"
        clean_pitch = pitch if pitch and ("Hz" in pitch or "%" in pitch) else "+0Hz"

        communicate = edge_tts.Communicate(
            text=text,
            voice=voice,
            rate=clean_rate,
            pitch=clean_pitch,
        )
        await communicate.save(output_path)

        if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"Edge TTS kon audio niet opslaan op {output_path}")

        return output_path

    async def generate_tts_piper(
        self,
        text: str,
        voice_id: str = "nl_NL-mls-medium",
        output_path: Optional[str] = None,
    ) -> str:
        """Genereer spraak met het lokale Piper TTS binaire model."""
        if not output_path:
            out_file = settings.audio_dir / f"piper_{uuid.uuid4().hex[:10]}.wav"
            output_path = str(out_file)

        model_dir = Path(settings_manager.get("piper_model_path", settings.piper_model_path))
        model_file = model_dir / f"{voice_id}.onnx"
        if not model_file.exists():
            onnx_files = list(model_dir.glob("*.onnx"))
            if onnx_files:
                model_file = onnx_files[0]
            else:
                logger.info("Geen lokaal Piper model gevonden op %s, val terug op Edge-TTS.", model_dir)
                return await self.generate_tts_edge(text=text, output_path=output_path)

        piper_bin = shutil.which("piper") or "/usr/local/bin/piper" or "/usr/bin/piper"
        if os.path.exists(piper_bin) and model_file.exists():
            proc = await asyncio.create_subprocess_exec(
                piper_bin,
                "--model",
                str(model_file),
                "--output_file",
                output_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
            if proc.returncode == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                return output_path
            logger.warning("Piper binary execution error: %s", stderr.decode(errors="replace"))

        # Fallback naar Edge-TTS
        return await self.generate_tts_edge(text=text, output_path=output_path)

    async def generate_tts_kokoro(
        self,
        text: str,
        voice_id: str = "af_bella",
        output_path: Optional[str] = None,
        language: str = "nl",
    ) -> str:
        """Genereer audio via de Kokoro TTS HTTP service."""
        import httpx

        if not output_path:
            out_file = settings.audio_dir / f"kokoro_{uuid.uuid4().hex[:10]}.wav"
            output_path = str(out_file)

        base_url = settings_manager.get("kokoro_base_url", settings.kokoro_base_url).rstrip("/")
        payload = {
            "text": text,
            "voice": voice_id or "af_bella",
            "lang": "nl" if language.startswith("nl") else "en",
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(f"{base_url}/v1/audio/speech", json=payload)
            if resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(resp.content)
                return output_path
            raise RuntimeError(f"Kokoro TTS server fout: {resp.status_code}")

    async def _generate_fallback_tts(self, text: str, output_path: str) -> str:
        """Systeemeigen fallback TTS generatie (macOS 'say' of gTTS / synth tone)."""
        import platform

        if platform.system() == "Darwin":
            say_bin = shutil.which("say")
            if say_bin:
                proc = await asyncio.create_subprocess_exec(
                    say_bin,
                    "-v",
                    "Claire",
                    "-o",
                    output_path,
                    "--data-format=LEF32@24000",
                    text,
                )
                await proc.communicate()
                if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                    return output_path

        # Indien Docker container: genereer via Google TTS als sleutel er is
        try:
            from app.services.gemini_service import gemini_service

            audio_bytes = await gemini_service.text_to_speech_google(text)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return output_path
        except Exception:
            pass

        # Uiterste nood-fallback: genereer een zachte, vrolijke kindertoon zodat de render doordraait
        words = len(text.split())
        est_duration = max(2.0, words * 0.4)
        import numpy as np

        sample_rate = 24000
        t = np.linspace(0, est_duration, int(sample_rate * est_duration), False)
        tone = 0.03 * np.sin(2 * np.pi * 523.25 * t)  # C5 toon
        sf.write(output_path, tone, sample_rate)
        return output_path

    async def generate_tts(
        self,
        text: str,
        voice_id: str = "",
        provider: str = "edge_tts",
        language: str = "nl",
        pitch: str = "+0Hz",
        rate: str = "+0%",
        output_path: Optional[str] = None,
    ) -> str:
        """Centrale dispatcher voor TTS generatie met Edge-TTS als primaire keuze."""
        if not output_path:
            ext = ".mp3" if "edge" in (provider or "edge_tts").lower() else ".wav"
            dest = settings.audio_dir / f"tts_{uuid.uuid4().hex[:10]}{ext}"
            output_path = str(dest)

        provider_norm = (provider or "edge_tts").lower().strip()

        # 1. Edge-TTS (Aanbevolen, gratis, hoogwaardig)
        if provider_norm in ("edge_tts", "edge", ""):
            try:
                active_voice = voice_id or "nl-NL-FennaNeural"
                return await self.generate_tts_edge(
                    text=text,
                    voice_id=active_voice,
                    rate=rate,
                    pitch=pitch,
                    output_path=output_path,
                )
            except Exception as e:
                logger.warning("Edge TTS faalde (%s); probeer Piper of Google fallback.", e)

        # 2. Google Cloud TTS
        if provider_norm == "google":
            try:
                from app.services.gemini_service import gemini_service

                audio_bytes = await gemini_service.text_to_speech_google(
                    text, voice_id=voice_id, language=language
                )
                with open(output_path, "wb") as f:
                    f.write(audio_bytes)
                return output_path
            except Exception as e:
                logger.warning("Google TTS faalde (%s); probeer Edge TTS.", e)
                return await self.generate_tts_edge(text=text, output_path=output_path)

        # 3. Kokoro TTS
        if provider_norm == "kokoro":
            try:
                return await self.generate_tts_kokoro(
                    text=text, voice_id=voice_id, output_path=output_path, language=language
                )
            except Exception as e:
                logger.warning("Kokoro faalde (%s), probeer Edge TTS.", e)
                return await self.generate_tts_edge(text=text, output_path=output_path)

        # 4. Piper TTS
        if provider_norm == "piper":
            try:
                return await self.generate_tts_piper(text=text, voice_id=voice_id, output_path=output_path)
            except Exception as e:
                logger.warning("Piper faalde (%s), val terug op Edge TTS.", e)
                return await self.generate_tts_edge(text=text, output_path=output_path)

        # Default fallback
        try:
            return await self.generate_tts_edge(text=text, output_path=output_path)
        except Exception:
            return await self._generate_fallback_tts(text, output_path)

    async def get_word_timestamps(self, audio_path: str) -> List[Dict[str, Any]]:
        """Extraheer woord-timestamps met faster-whisper voor exacte lip-sync."""
        p = Path(audio_path)
        if not p.exists() or p.stat().st_size == 0:
            return []

        def _transcribe():
            model = self._get_whisper_model()
            if model is None:
                return []
            try:
                segments, _ = model.transcribe(
                    str(p),
                    word_timestamps=True,
                    language="nl",
                    vad_filter=True,
                )
                words = []
                for segment in segments:
                    if segment.words:
                        for w in segment.words:
                            words.append(
                                {
                                    "word": w.word.strip(),
                                    "start": round(w.start, 2),
                                    "end": round(w.end, 2),
                                    "probability": round(w.probability, 2),
                                }
                            )
                    else:
                        words.append(
                            {
                                "word": segment.text.strip(),
                                "start": round(segment.start, 2),
                                "end": round(segment.end, 2),
                                "probability": 1.0,
                            }
                        )
                return words
            except Exception as exc:
                logger.warning("Transcriptie fout in faster-whisper: %s", exc)
                return []

        try:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(None, _transcribe)
            if res:
                return res
        except Exception as e:
            logger.warning("Fout bij uitvoeren whisper transcriptie: %s", e)

        # Synthetische timestamps schatting als whisper niet draait
        duration = self.get_audio_duration(audio_path)
        return [{"word": "spraak", "start": 0.0, "end": max(1.0, duration), "probability": 1.0}]


audio_service = AudioService()
