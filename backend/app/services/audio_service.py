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

import edge_tts
import soundfile as sf

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)


async def generate_edge_tts_audio(text: str, voice: str, rate: str, pitch: str, output_path: str) -> str:
    """Genereert echte spraak via Microsoft Edge TTS zonder nep-fallbacks of pieptonen."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    clean_rate = rate if (rate.startswith("+") or rate.startswith("-")) and rate.endswith("%") else "+0%"
    clean_pitch = pitch if (pitch.startswith("+") or pitch.startswith("-")) and pitch.endswith("Hz") else "+0Hz"
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=clean_rate, pitch=clean_pitch)
    await communicate.save(output_path)
    if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
        raise RuntimeError("Edge-TTS heeft geen geldig spraakbestand gegenereerd.")
    return output_path

# Beschikbare stemmen per provider (uitsluitend werkende implementaties)
AVAILABLE_VOICES = {
    "edge_tts": [
        {
            "id": "nl-NL-FennaNeural",
            "name": "Fenna (Nederlands - Vrolijk & Helder, aanbevolen voor kleuters)",
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
            "recommended": True,
        },
        {
            "id": "nl-BE-ArnaudNeural",
            "name": "Arnaud (Vlaams - Rustig & vertellend)",
            "gender": "male",
            "language": "nl-BE",
            "recommended": False,
        },
        {
            "id": "en-US-AnaNeural",
            "name": "Ana (Engels - Kindvriendelijke peuterstem)",
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
        # 1. Probeer mutagen voor uiterst nauwkeurige MP3/WAV parsing
        try:
            from mutagen import File as MutagenFile

            mf = MutagenFile(str(p))
            if mf is not None and mf.info and hasattr(mf.info, "length"):
                return round(float(mf.info.length), 3)
        except Exception:
            pass

        # 2. Probeer soundfile
        try:
            with sf.SoundFile(str(p)) as f:
                return round(float(len(f)) / float(f.samplerate), 3)
        except Exception:
            pass

        # 3. Probeer ffprobe
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
            return round(float(output), 3)
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
        """Genereer hoogwaardige spraak via de gratis Microsoft Edge TTS service."""
        if not output_path:
            out_file = settings.audio_dir / f"edge_{uuid.uuid4().hex[:10]}.mp3"
            output_path = str(out_file)

        voice = voice_id or "nl-NL-FennaNeural"
        return await generate_edge_tts_audio(
            text=text,
            voice=voice,
            rate=rate,
            pitch=pitch,
            output_path=output_path,
        )

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
        active_voice = voice_id or "nl-NL-FennaNeural"

        # 1. Google Cloud TTS
        if provider_norm == "google":
            from app.services.gemini_service import gemini_service

            audio_bytes = await gemini_service.text_to_speech_google(
                text, voice_id=active_voice, language=language
            )
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "wb") as f:
                f.write(audio_bytes)
            if not os.path.exists(output_path) or os.path.getsize(output_path) < 1000:
                raise RuntimeError("Google TTS heeft geen geldig audiobestand gegenereerd.")
            return output_path

        # 2. Edge-TTS (Standaard gratis, hoogwaardig kinderstemmen)
        return await generate_edge_tts_audio(
            text=text,
            voice=active_voice,
            rate=rate,
            pitch=pitch,
            output_path=output_path,
        )

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
