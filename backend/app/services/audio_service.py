"""Audio & Text-to-Speech service voor AI-Studio.

Ondersteunt Piper TTS (lokaal/snel), Kokoro TTS (high quality REST),
Google Cloud TTS, en analyseert audio met faster-whisper voor exacte
woord-level timestamps t.b.v. lip-sync animaties.
"""

import asyncio
import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import soundfile as sf

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


class AudioService:
    """Service voor spraaksynthese en audioverwerking."""

    def __init__(self):
        self._whisper_model = None

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
        if not p.exists():
            return 0.0
        try:
            with sf.SoundFile(str(p)) as f:
                return float(len(f)) / float(f.samplerate)
        except Exception as e:
            logger.warning("Fout bij uitlezen duur via soundfile (%s), probeer ffprobe.", e)
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

    async def generate_tts_piper(
        self,
        text: str,
        voice_id: str = "nl_NL-mls-medium",
        output_path: Optional[str] = None,
    ) -> str:
        """Genereer spraak met het lokale Piper TTS binaire model."""
        if not output_path:
            out_file = settings.audio_dir / f"piper_{os.urandom(6).hex()}.wav"
            output_path = str(out_file)

        model_dir = Path(settings_manager.get("piper_model_path", settings.piper_model_path))
        # Zoek naar .onnx modelbestand
        model_file = model_dir / f"{voice_id}.onnx"
        if not model_file.exists():
            # Kijk of er überhaupt een onnx bestand in de map staat
            onnx_files = list(model_dir.glob("*.onnx"))
            if onnx_files:
                model_file = onnx_files[0]
            else:
                logger.info("Geen lokaal Piper model gevonden op %s, val terug op synthesizer.", model_dir)

        # Probeer piper binary via shell
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
            if proc.returncode == 0 and os.path.exists(output_path):
                return output_path
            logger.warning("Piper binary execution error: %s", stderr.decode())

        # Fallback: Genereer spraak via Python espeak of say op macOS / gTTS fallback
        return await self._generate_fallback_tts(text, output_path)

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
            out_file = settings.audio_dir / f"kokoro_{os.urandom(6).hex()}.wav"
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

        # Indien Docker container: genereer via gemini TTS of spraak-synthese
        try:
            from app.services.gemini_service import gemini_service

            audio_bytes = await gemini_service.text_to_speech_google(text)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return output_path
        except Exception:
            pass

        # Uiterste nood-fallback: Schrijf een stilte/toon audiobestand met juiste geschatte lengte
        words = len(text.split())
        est_duration = max(2.0, words * 0.4)
        import numpy as np

        sample_rate = 24000
        t = np.linspace(0, est_duration, int(sample_rate * est_duration), False)
        # Zeer zachte vrolijke toonreeks (440Hz arpeggio) zodat render niet vastloopt
        tone = 0.05 * np.sin(2 * np.pi * 440 * t)
        sf.write(output_path, tone, sample_rate)
        return output_path

    async def generate_tts(
        self,
        text: str,
        voice_id: str = "",
        provider: str = "piper",
        language: str = "nl",
        output_path: Optional[str] = None,
    ) -> str:
        """Centrale dispatcher voor TTS generatie."""
        if not output_path:
            dest = settings.audio_dir / f"tts_{os.urandom(6).hex()}.wav"
            output_path = str(dest)

        provider_norm = (provider or "piper").lower()

        if provider_norm == "google":
            from app.services.gemini_service import gemini_service

            audio_bytes = await gemini_service.text_to_speech_google(text, voice_id=voice_id, language=language)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            return output_path

        if provider_norm == "kokoro":
            try:
                return await self.generate_tts_kokoro(
                    text=text, voice_id=voice_id, output_path=output_path, language=language
                )
            except Exception as e:
                logger.warning("Kokoro faalde (%s), probeer Piper.", e)

        # Standaard: Piper
        try:
            return await self.generate_tts_piper(text=text, voice_id=voice_id, output_path=output_path)
        except Exception as e:
            logger.warning("Piper faalde (%s), activeer fallback.", e)
            return await self._generate_fallback_tts(text, output_path)

    async def get_word_timestamps(self, audio_path: str) -> List[Dict[str, Any]]:
        """Extraheer woord-timestamps met faster-whisper voor exacte lip-sync.

        Geeft een lijst terug van dictionaries: [{"word": "hallo", "start": 0.1, "end": 0.5}, ...]
        """
        p = Path(audio_path)
        if not p.exists():
            return []

        def _transcribe():
            model = self._get_whisper_model()
            if model is None:
                return []
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

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(None, _transcribe)
        except Exception as e:
            logger.warning("Fout bij extraheren timestamps met faster-whisper: %s", e)
            # Synthetische timestamps schatting
            duration = self.get_audio_duration(audio_path)
            return [{"word": "spraak", "start": 0.0, "end": max(1.0, duration), "probability": 1.0}]


audio_service = AudioService()

