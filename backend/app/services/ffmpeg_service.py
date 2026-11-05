"""FFmpeg video- en audio-rendering service voor AI-Studio.

Biedt:
- 2.5D Ken Burns zoompan animaties
- Scène-overgangen (xfade: crossfade, fadeblack, slideleft, wipeleft)
- Lip-sync animatie m.b.v. mond-sprites en audio timestamps
- Multi-track audiomixing met sidechain ducking
- EBU R128 (-14 LUFS) audionormalisatie
- Volledige multi-scène episode rendering pipeline
"""

import asyncio
import json
import logging
import math
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class FFmpegService:
    """Service voor FFmpeg video rendering en audiomixing."""

    def __init__(self):
        self.ffmpeg_bin = shutil.which("ffmpeg") or "/usr/bin/ffmpeg"
        self.ffprobe_bin = shutil.which("ffprobe") or "/usr/bin/ffprobe"

    async def _run_command(self, cmd: List[str]) -> None:
        """Voer een ffmpeg/ffprobe commando asynchroon uit."""
        cmd_str = " ".join(cmd)
        logger.debug("Uitvoeren FFmpeg: %s", cmd_str)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            err = stderr.decode(errors="replace")
            logger.error("FFmpeg fout (%s): %s", proc.returncode, err[-500:])
            raise RuntimeError(f"FFmpeg fout: {err[-300:]}")

    async def apply_ken_burns(
        self,
        image_path: str,
        duration: float,
        output_path: str,
        direction: str = "zoom_in",
        width: int = 1920,
        height: int = 1080,
        fps: int = 30,
    ) -> str:
        """Maak een vloeiende Ken Burns bewegingsclip van een statische afbeelding."""
        total_frames = int(max(1.0, duration) * fps)

        # zoompan expressies afhankelijk van gewenste richting
        if direction in ("ken_burns", "zoom", "zoom_in"):
            # Standaard Ken Burns: rustige zoom-in.
            zoom_expr = f"min(pzoom+0.0005,1.15)"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif direction == "zoom_out":
            zoom_expr = f"if(eq(on,0),1.15,max(1.0,pzoom-0.0005))"
            x_expr = "iw/2-(iw/zoom/2)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif direction == "pan_left":
            zoom_expr = "1.1"
            x_expr = f"(1-on/{total_frames})*(iw-iw/zoom)"
            y_expr = "ih/2-(ih/zoom/2)"
        elif direction == "pan_right":
            zoom_expr = "1.1"
            x_expr = f"(on/{total_frames})*(iw-iw/zoom)"
            y_expr = "ih/2-(ih/zoom/2)"
        else:
            zoom_expr = "1.0"
            x_expr = "0"
            y_expr = "0"

        filter_str = (
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}':"
            f"d={total_frames}:s={width}x{height}:fps={fps},"
            f"format=yuv420p"
        )

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-loop",
            "1",
            "-i",
            image_path,
            "-vf",
            filter_str,
            "-t",
            str(duration),
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
        await self._run_command(cmd)
        return output_path

    async def apply_transition(
        self,
        clip1_path: str,
        clip2_path: str,
        transition_type: str = "crossfade",
        duration: float = 1.0,
        output_path: str = "",
    ) -> str:
        """Voeg twee videoclips samen met een xfade overgang."""
        if not output_path:
            output_path = str(settings.temp_dir / f"trans_{uuid.uuid4().hex[:8]}.mp4")

        # Bepaal duur van clip1
        dur1 = await self.get_duration(clip1_path)
        offset = max(0.1, dur1 - duration)

        xfade_name = "fade"
        if transition_type == "slide_left":
            xfade_name = "slideleft"
        elif transition_type == "slide_right":
            xfade_name = "slideright"
        elif transition_type == "wipe":
            xfade_name = "wipeleft"
        elif transition_type == "fade_black":
            xfade_name = "fadeblack"

        filter_complex = f"[0:v][1:v]xfade=transition={xfade_name}:duration={duration}:offset={offset}[v]"

        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            clip1_path,
            "-i",
            clip2_path,
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            output_path,
        ]
        await self._run_command(cmd)
        return output_path

    async def create_lip_sync_video(
        self,
        base_scene_video: str,
        mouth_open_path: Optional[str],
        mouth_closed_path: Optional[str],
        audio_path: str,
        timestamps: List[Dict[str, Any]],
        output_path: str,
        speaker: str = "verteller",
        mouth_x: int = 960,
        mouth_y: int = 700,
    ) -> str:
        """Voeg gesproken audio toe en animeer mond-sprites tijdens gesproken intervallen.
        
        Als speaker 'verteller' is, bewegen de karakters niet mee (puur voice-over).
        """
        resolved_open = self._resolve_media_path(mouth_open_path)
        speaker_lower = (speaker or "").lower().strip()

        # Als er geen spreker is of spreker is de verteller: géén mond-animatie nodig
        if not resolved_open or speaker_lower in ("verteller", "voiceover", "voice-over", "geen", ""):
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                base_scene_video,
                "-i",
                audio_path,
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-shortest",
                output_path,
            ]
            await self._run_command(cmd)
            return output_path

        # Bereken tijdsintervallen waarin de mond open gaat
        conditions = []
        for ts in (timestamps or []):
            st = float(ts.get("start", 0))
            en = float(ts.get("end", 0))
            if en > st and (en - st) >= 0.05:
                conditions.append(f"between(t,{st:.2f},{en:.2f})")

        if conditions:
            # Combineer intervallen
            enable_expr = "+".join(conditions[:60])
        else:
            enable_expr = "between(t,0.3,5.0)"

        overlay_filter = f"[0:v][1:v]overlay=x={mouth_x}:y={mouth_y}:enable='{enable_expr}'[v]"
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-i",
            base_scene_video,
            "-i",
            resolved_open,
            "-i",
            audio_path,
            "-filter_complex",
            overlay_filter,
            "-map",
            "[v]",
            "-map",
            "2:a",
            "-c:v",
            "libx264",
            "-c:a",
            "aac",
            "-shortest",
            output_path,
        ]
        try:
            await self._run_command(cmd)
            return output_path
        except Exception as exc:
            logger.warning("Lip-sync filter faalde (%s); val terug op directe audiokoppeling.", exc)
            return await self.create_lip_sync_video(
                base_scene_video, None, None, audio_path, [], output_path, speaker="verteller"
            )

    async def mix_audio_tracks(
        self,
        narration_path: Optional[str],
        music_path: Optional[str],
        output_path: str,
        target_lufs: float = -14.0,
    ) -> str:
        """Mix gesproken stem en achtergrondmuziek met sidechain ducking en -14 LUFS normalisatie."""
        if narration_path and not music_path:
            # Enkel normaliseren naar -14 LUFS
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                narration_path,
                "-af",
                f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                output_path,
            ]
            await self._run_command(cmd)
            return output_path

        if narration_path and music_path:
            # Sidechain ducking: muziek automatisch dimmen wanneer stem actief is
            filter_complex = (
                "[1:a]volume=0.25[bgm];"
                "[bgm][0:a]sidechaincompress=threshold=0.125:ratio=4:attack=50:release=300[ducked];"
                "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=2,"
                f"loudnorm=I={target_lufs}:TP=-1.0:LRA=11[aout]"
            )
            cmd = [
                self.ffmpeg_bin,
                "-y",
                "-i",
                narration_path,
                "-i",
                music_path,
                "-filter_complex",
                filter_complex,
                "-map",
                "[aout]",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                output_path,
            ]
            await self._run_command(cmd)
            return output_path

        # Indien geen narration: genereer 5 seconden stilte
        cmd = [
            self.ffmpeg_bin,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=44100:cl=stereo",
            "-t",
            "5",
            "-c:a",
            "aac",
            output_path,
        ]
        await self._run_command(cmd)
        return output_path

    async def _has_audio(self, file_path: str) -> bool:
        """Controleer of een mediabestand een audiospoor bevat."""
        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            file_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        return bool(stdout.decode(errors="replace").strip())

    async def get_duration(self, file_path: str) -> float:
        """Haal de duur op via ffprobe."""
        cmd = [
            self.ffprobe_bin,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            file_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        try:
            return float(stdout.decode().strip())
        except Exception:
            return 8.0

    @staticmethod
    def _resolve_media_path(path: Optional[str]) -> Optional[str]:
        """Accepteer zowel absolute paden als /api/media/ of /media/ URL's."""
        if not path:
            return None
        p = str(path).strip()
        if not p:
            return None
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
        if p.startswith("/api/media/"):
            candidate = settings.media_dir / p[len("/api/media/") :]
            if candidate.exists() and candidate.stat().st_size > 0:
                return str(candidate)
        if p.startswith("/media/"):
            candidate = settings.media_dir / p[len("/media/") :]
            if candidate.exists() and candidate.stat().st_size > 0:
                return str(candidate)
        if p.startswith("/data/media/"):
            candidate = settings.media_dir / p[len("/data/media/") :]
            if candidate.exists() and candidate.stat().st_size > 0:
                return str(candidate)
        return None

    @staticmethod
    def _xfade_name(transition_type: str) -> str:
        """Vertaal een UI-overgang naar een geldige FFmpeg xfade-transitie."""
        name = (transition_type or "crossfade").lower().replace("-", "_").replace(" ", "_")
        return {
            "crossfade": "fade",
            "fade": "fade",
            "dissolve": "dissolve",
            "cross_dissolve": "dissolve",
            "fade_black": "fadeblack",
            "dip_to_black": "fadeblack",
            "fade_white": "fadewhite",
            "dip_to_white": "fadewhite",
            "wipe": "wipeleft",
            "wipe_left": "wipeleft",
            "wipe_right": "wiperight",
            "circle_wipe": "circleopen",
            "circleopen": "circleopen",
            "slide": "slideleft",
            "slide_left": "slideleft",
            "slide_right": "slideright",
            "star": "circleopen",
            "star_bumper": "circleopen",
            "cut": "fade",
            "hard_cut": "fade",
            "none": "fade",
            "static": "fade",
            "smoothleft": "smoothleft",
            "smoothright": "smoothright",
        }.get(name, "fade")

    def _transition_duration(self, transition_type: str, dur_a: float, dur_b: float) -> float:
        """Bepaal een veilige overgangsduur voor twee scènes."""
        name = (transition_type or "").lower().replace("-", "_")
        if name in ("cut", "hard_cut", "none", "static", ""):
            return 0.04
        # Nooit meer dan een kwart van de kortste scène innemen.
        return max(0.04, min(0.6, dur_a * 0.25, dur_b * 0.25))

    async def _scene_clip(
        self,
        image_path: str,
        audio_path: Optional[str],
        sfx_path: Optional[str],
        duration: float,
        output_path: str,
        direction: str,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        """Render één scène met exact dezelfde duur voor video en audio."""
        duration = max(0.5, float(duration))
        silent_video = str(Path(output_path).with_name(f"{Path(output_path).stem}_video.mp4"))

        await self.apply_ken_burns(
            image_path=image_path,
            duration=duration,
            output_path=silent_video,
            direction=direction,
            width=width,
            height=height,
            fps=fps,
        )

        cmd = [self.ffmpeg_bin, "-y", "-i", silent_video]
        audio_filter: Optional[str] = None

        resolved_audio = self._resolve_media_path(audio_path)
        resolved_sfx = self._resolve_media_path(sfx_path)

        if resolved_audio:
            cmd += ["-i", resolved_audio]
            filters = [
                (
                    f"[1:a]aresample=44100,"
                    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"apad=whole_dur={duration:.3f},"
                    f"atrim=duration={duration:.3f},asetpts=PTS-STARTPTS[a1]"
                )
            ]
            if resolved_sfx:
                cmd += ["-i", resolved_sfx]
                filters.append(
                    (
                        f"[2:a]aresample=44100,"
                        "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                        "volume=0.25,"
                        f"apad=whole_dur={duration:.3f},"
                        f"atrim=duration={duration:.3f},asetpts=PTS-STARTPTS[a2]"
                    )
                )
                filters.append(
                    "[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
            else:
                filters.append("[a1]anull[aout]")
            audio_filter = ";".join(filters)
        elif resolved_sfx:
            cmd += ["-i", resolved_sfx]
            audio_filter = (
                "[1:a]aresample=44100,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                "volume=0.25,"
                f"apad=whole_dur={duration:.3f},"
                f"atrim=duration={duration:.3f},asetpts=PTS-STARTPTS[aout]"
            )

        if audio_filter:
            cmd += [
                "-filter_complex",
                audio_filter,
                "-map",
                "0:v:0",
                "-map",
                "[aout]",
            ]
        else:
            # Stil audiospoor zodat elke scène even lang is en acrossfade werkt.
            cmd += [
                "-f",
                "lavfi",
                "-t",
                f"{duration:.3f}",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
            ]

        cmd += [
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-t",
            f"{duration:.3f}",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_command(cmd)
        return output_path

    async def _animated_scene_clip(
        self,
        video_path: str,
        audio_path: Optional[str],
        sfx_path: Optional[str],
        target_duration: float,
        output_path: str,
        width: int,
        height: int,
        fps: int,
    ) -> str:
        """Synchroniseert een AI-gegenereerde videoclip (Veo, Wan) exact met de audio.
        
        Gebruikt time-stretch (setpts) als het verschil < 30% is, of een naadloze
        ping-pong loop (vooruit + achteruit) zodat de videoclip op de milliseconde
        aansluit op de gesproken kinderteksst zonder zwarte beelden of abrupte freeze frames.
        """
        source_dur = await self.get_duration(video_path)
        source_dur = max(0.5, source_dur)
        target_dur = max(0.5, float(target_duration))

        # Schaal & normaliseer filter
        base_scale = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            f"fps={fps},format=yuv420p"
        )

        ratio = target_dur / source_dur

        if 0.7 <= ratio <= 1.3:
            # Vloeiende snelheidsaanpassing (Time-stretch)
            video_filter = f"{base_scale},setpts={ratio:.4f}*PTS,trim=duration={target_dur:.3f}"
            inputs = ["-i", video_path]
        elif target_dur > source_dur:
            # Ping-pong loop (vooruit + achteruit) om naadloos de langere spraakduur te vullen
            # Maak een loop van bron + reverse
            loops_needed = int(math.ceil(target_dur / (source_dur * 2))) + 1
            loop_filter = (
                f"[0:v]{base_scale},split=2[v_fwd][v_rev_in];"
                f"[v_rev_in]reverse[v_rev];"
                f"[v_fwd][v_rev]concat=n=2:v=1:a=0[v_pingpong];"
                f"[v_pingpong]loop=loop={loops_needed}:size=32767:start=0,"
                f"trim=duration={target_dur:.3f},setpts=PTS-STARTPTS[vout]"
            )
            video_filter = loop_filter
            inputs = ["-i", video_path]
        else:
            # Clip is langer dan nodig: trim netjes af
            video_filter = f"{base_scale},trim=duration={target_dur:.3f},setpts=PTS-STARTPTS"
            inputs = ["-i", video_path]

        cmd = [self.ffmpeg_bin, "-y"] + inputs

        resolved_audio = self._resolve_media_path(audio_path)
        resolved_sfx = self._resolve_media_path(sfx_path)

        if resolved_audio:
            cmd += ["-i", resolved_audio]
            audio_filters = [
                (
                    f"[1:a]aresample=44100,"
                    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"apad=whole_dur={target_dur:.3f},"
                    f"atrim=duration={target_dur:.3f},asetpts=PTS-STARTPTS[a1]"
                )
            ]
            if resolved_sfx:
                cmd += ["-i", resolved_sfx]
                audio_filters.append(
                    (
                        f"[2:a]aresample=44100,"
                        "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                        "volume=0.25,"
                        f"apad=whole_dur={target_dur:.3f},"
                        f"atrim=duration={target_dur:.3f},asetpts=PTS-STARTPTS[a2]"
                    )
                )
                audio_filters.append(
                    "[a1][a2]amix=inputs=2:duration=first:dropout_transition=2[aout]"
                )
            else:
                audio_filters.append("[a1]anull[aout]")
            audio_str = ";".join(audio_filters)
        elif resolved_sfx:
            cmd += ["-i", resolved_sfx]
            audio_str = (
                "[1:a]aresample=44100,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                "volume=0.25,"
                f"apad=whole_dur={target_dur:.3f},"
                f"atrim=duration={target_dur:.3f},asetpts=PTS-STARTPTS[aout]"
            )
        else:
            audio_str = None

        if "concat" in video_filter:
            # Filter complex met meerdere labels
            if audio_str:
                full_filter = f"{video_filter};{audio_str}"
                cmd += [
                    "-filter_complex",
                    full_filter,
                    "-map",
                    "[vout]",
                    "-map",
                    "[aout]",
                ]
            else:
                cmd += [
                    "-filter_complex",
                    video_filter,
                    "-map",
                    "[vout]",
                    "-f",
                    "lavfi",
                    "-t",
                    f"{target_dur:.3f}",
                    "-i",
                    "anullsrc=r=44100:cl=stereo",
                    "-map",
                    "1:a:0",
                ]
        else:
            # Eenvoudige filter
            if audio_str:
                full_filter = f"[0:v]{video_filter}[vout];{audio_str}"
                cmd += [
                    "-filter_complex",
                    full_filter,
                    "-map",
                    "[vout]",
                    "-map",
                    "[aout]",
                ]
            else:
                cmd += [
                    "-vf",
                    video_filter,
                    "-f",
                    "lavfi",
                    "-t",
                    f"{target_dur:.3f}",
                    "-i",
                    "anullsrc=r=44100:cl=stereo",
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                ]

        cmd += [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-t",
            f"{target_dur:.3f}",
            "-movflags",
            "+faststart",
            output_path,
        ]

        await self._run_command(cmd)
        return output_path

    async def _video_clip(
        self,
        video_path: str,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        duration: Optional[float] = None,
    ) -> str:
        """Normaliseer een bestaande videoclip (bijv. intro/outro bumper) naar
        dezelfde resolutie, fps en exacte duur als de scèneclips."""
        source_duration = await self.get_duration(video_path)
        dur = float(duration) if duration else source_duration
        # Een bumper mag nooit langer worden dan het bronbestand.
        dur = max(0.5, min(dur, source_duration))
        has_audio = await self._has_audio(video_path)

        video_filter = (
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
            f"fps={fps},format=yuv420p"
        )

        cmd = [self.ffmpeg_bin, "-y", "-i", video_path]
        if has_audio:
            cmd += [
                "-vf",
                video_filter,
                "-af",
                (
                    "aresample=44100,"
                    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    f"apad=whole_dur={dur:.3f},atrim=duration={dur:.3f}"
                ),
                "-map",
                "0:v:0",
                "-map",
                "0:a:0",
            ]
        else:
            cmd += [
                "-vf",
                video_filter,
                "-f",
                "lavfi",
                "-t",
                f"{dur:.3f}",
                "-i",
                "anullsrc=r=44100:cl=stereo",
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
            ]

        cmd += [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-t",
            f"{dur:.3f}",
            "-movflags",
            "+faststart",
            output_path,
        ]
        await self._run_command(cmd)
        return output_path

    async def render_episode(
        self,
        scenes_data: List[Dict[str, Any]],
        output_path: str,
        resolution: str = "1920x1080",
        fps: int = 30,
        bg_music_path: Optional[str] = None,
        intro_path: Optional[str] = None,
        outro_path: Optional[str] = None,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> str:
        """Volledige end-to-end rendering pipeline voor een aflevering.

        Elke scène wordt op exact dezelfde duur gebracht (audio wordt aangevuld
        met stilte of afgekapt), daarna via xfade/acrossfade aan elkaar gezet en
        tot slot gemasterd met optionele achtergrondmuziek en sidechain ducking.
        Optionele vaste intro/outro bumpers worden als volwaardige segmenten
        vooraan/achteraan de montage toegevoegd.
        """
        try:
            w, h = [int(x) for x in resolution.split("x")]
        except Exception:
            w, h = 1920, 1080

        temp_dir = Path(tempfile.mkdtemp(prefix="render_ep_"))
        scene_clips: List[str] = []
        scene_durations: List[float] = []

        # Bumpers worden tijdelijke segmenten met dezelfde verwerking als scènes.
        segments: List[Dict[str, Any]] = []
        if intro_path:
            segments.append(
                {
                    "title": "Intro bumper",
                    "video_path": intro_path,
                    "animation_type": "static",
                    "transition_type": "crossfade",
                }
            )
        segments.extend(scenes_data)
        if outro_path:
            segments.append(
                {
                    "title": "Outro bumper",
                    "video_path": outro_path,
                    "animation_type": "static",
                    "transition_type": "crossfade",
                }
            )
        total_scenes = len(segments)

        try:
            # Stap 1: Render individuele scènes naar clips met vaste duur
            for idx, sc in enumerate(segments):
                if progress_callback:
                    pct = 0.05 + (0.55 * (idx / max(1, total_scenes)))
                    progress_callback(
                        pct,
                        f"Scène {idx + 1}/{total_scenes} verwerken "
                        f"({sc.get('title', '')})...",
                    )

                clip_out = str(temp_dir / f"scene_{idx:03d}.mp4")
                video_clip_path = self._resolve_media_path(
                    sc.get("video_clip_path") or sc.get("video_path")
                )
                dur = max(0.5, float(sc.get("duration_seconds", 8.0) or 8.0))

                if video_clip_path and sc.get("title", "").endswith("bumper"):
                    # Vaste intro/outro bumper
                    await self._video_clip(
                        video_path=video_clip_path,
                        output_path=clip_out,
                        width=w,
                        height=h,
                        fps=fps,
                        duration=dur,
                    )
                elif video_clip_path:
                    # Echte geanimeerde videoclip (Google Veo, Wan 2.1 of Drag & Drop upload)
                    await self._animated_scene_clip(
                        video_path=video_clip_path,
                        audio_path=sc.get("audio_path"),
                        sfx_path=sc.get("sfx_track"),
                        target_duration=dur,
                        output_path=clip_out,
                        width=w,
                        height=h,
                        fps=fps,
                    )
                else:
                    # 2.5D Ken Burns Fallback met het Start-Frame
                    img_path = self._resolve_media_path(
                        sc.get("composite_image_path")
                        or sc.get("background_image_path")
                    )
                    if not img_path:
                        raise RuntimeError(
                            f"Scène {idx + 1} ('{sc.get('title', 'Zonder titel')}') heeft geen geldige Start-Frame afbeelding op schijf. "
                            f"Genereer of upload eerst een afbeelding voor deze scène in de studio."
                        )

                    await self._scene_clip(
                        image_path=img_path,
                        audio_path=sc.get("audio_path"),
                        sfx_path=sc.get("sfx_track"),
                        duration=dur,
                        output_path=clip_out,
                        direction=sc.get("animation_type", "ken_burns"),
                        width=w,
                        height=h,
                        fps=fps,
                    )
                scene_clips.append(clip_out)
                scene_durations.append(await self.get_duration(clip_out))

            if not scene_clips:
                raise RuntimeError("Geen scènes om te renderen.")

            # Stap 2: Overgangen + audiomixing in één filtergraaf
            if progress_callback:
                progress_callback(
                    0.68, "Scènes samenvoegen, overgangen en audio mixen..."
                )

            filters: List[str] = []
            for i, _clip in enumerate(scene_clips):
                # Alleen fps normaliseren: setpts/settb laten xfade zijn frame-rate
                # metadata verliezen (FFmpeg: "current rate of 1/0 is invalid").
                filters.append(f"[{i}:v]fps={fps}[pv{i}]")
                filters.append(f"[{i}:a]asetpts=PTS-STARTPTS[pa{i}]")

            transitions: List[float] = []
            video_label = "pv0"
            audio_label = "pa0"
            for i in range(1, len(scene_clips)):
                trans_type = str(segments[i - 1].get("transition_type", "crossfade"))
                td = self._transition_duration(
                    trans_type, scene_durations[i - 1], scene_durations[i]
                )
                transitions.append(td)
                offset = sum(scene_durations[:i]) - sum(transitions)
                xfade_name = self._xfade_name(trans_type)
                next_video = f"xv{i}"
                next_audio = f"xa{i}"
                filters.append(
                    f"[{video_label}][pv{i}]xfade=transition={xfade_name}:"
                    f"duration={td:.3f}:offset={max(0.0, offset):.3f}[{next_video}]"
                )
                filters.append(
                    f"[{audio_label}][pa{i}]acrossfade=d={td:.3f}:c1=tri:c2=tri[{next_audio}]"
                )
                video_label = next_video
                audio_label = next_audio

            total_duration = max(
                0.5, sum(scene_durations) - sum(transitions)
            )

            # Achtergrondmuziek met automatische ducking
            resolved_music = self._resolve_media_path(bg_music_path)
            cmd = [self.ffmpeg_bin, "-y"]
            for clip in scene_clips:
                cmd += ["-i", clip]

            if resolved_music:
                music_index = len(scene_clips)
                cmd += ["-stream_loop", "-1", "-i", resolved_music]
                fade_start = max(0.0, total_duration - 2.0)
                filters.append(
                    f"[{music_index}:a]aresample=44100,"
                    "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                    "volume=0.22,"
                    f"atrim=duration={total_duration:.3f},"
                    f"afade=t=out:st={fade_start:.3f}:d=2[bgm]"
                )
                filters.append(
                    "[bgm]["
                    + audio_label
                    + "]sidechaincompress=threshold=0.08:ratio=6:"
                    "attack=20:release=350[ducked]"
                )
                filters.append(
                    f"[{audio_label}][ducked]amix=inputs=2:duration=first:"
                    "dropout_transition=2,"
                    "loudnorm=I=-14:TP=-1.0:LRA=11[afinal]"
                )
            else:
                filters.append(
                    f"[{audio_label}]loudnorm=I=-14:TP=-1.0:LRA=11[afinal]"
                )

            cmd += [
                "-filter_complex",
                ";".join(filters),
                "-map",
                f"[{video_label}]",
                "-map",
                "[afinal]",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-r",
                str(fps),
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-t",
                f"{total_duration:.3f}",
                "-movflags",
                "+faststart",
                output_path,
            ]

            if progress_callback:
                progress_callback(0.82, "Video encoderen en -14 LUFS masteren...")

            await self._run_command(cmd)

            if progress_callback:
                progress_callback(1.0, "Render voltooid!")

            return output_path

        finally:
            # Ruim tijdelijke bestanden netjes op
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass


ffmpeg_service = FFmpegService()

