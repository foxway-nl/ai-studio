"""Audio API router – audio tracks, TTS synthese en uploads."""

import logging
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlmodel import Session, select

from app.core.config import settings
from app.core.database import get_session
from app.models.models import AudioTrack, Episode
from app.schemas.schemas import AudioTrackCreate, AudioTrackResponse, AudioTrackUpdate
from app.workers.task_manager import task_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/episodes/{episode_id}/audio", tags=["Audio"])


@router.get("", response_model=List[AudioTrackResponse])
@router.get("/", response_model=List[AudioTrackResponse])
async def list_audio_tracks(episode_id: str, session: Session = Depends(get_session)):
    """Lijst alle audiotracks (stem, muziek, effecten) van een aflevering op."""
    tracks = session.exec(
        select(AudioTrack).where(AudioTrack.episode_id == episode_id).order_by(AudioTrack.start_time.asc())
    ).all()
    return tracks


@router.post("/generate", response_model=AudioTrackResponse, status_code=201)
async def generate_narration_track(
    episode_id: str,
    data: AudioTrackCreate,
    text: str = "",
    session: Session = Depends(get_session),
):
    """Genereer een TTS audio track voor een aflevering."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    from app.services.audio_service import audio_service

    out_file = settings.audio_dir / f"track_{episode_id}_{uuid.uuid4().hex[:6]}.wav"
    audio_path = await audio_service.generate_tts(
        text=text or episode.title,
        voice_id=data.voice_id,
        provider=data.voice_provider,
        output_path=str(out_file),
    )

    duration = audio_service.get_audio_duration(audio_path)
    timestamps = await audio_service.get_word_timestamps(audio_path)
    import json

    track = AudioTrack(
        episode_id=episode_id,
        track_type=data.track_type or "narration",
        name=data.name or "Gesproken tekst",
        file_path=f"/media/audio/{out_file.name}",
        duration_seconds=duration,
        volume=data.volume,
        start_time=data.start_time,
        voice_id=data.voice_id,
        voice_provider=data.voice_provider,
        word_timestamps=json.dumps(timestamps),
        status="ready",
    )
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


@router.post("/upload", response_model=AudioTrackResponse, status_code=201)
async def upload_audio_track(
    episode_id: str,
    track_type: str = "music",
    name: str = "Achtergrondmuziek",
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    """Upload een eigen audiobestand (bv. vrolijke kinderachtergrondmuziek of geluidseffect)."""
    episode = session.get(Episode, episode_id)
    if not episode:
        raise HTTPException(status_code=404, detail="Aflevering niet gevonden.")

    ext = Path(file.filename).suffix if file.filename else ".mp3"
    filename = f"user_{episode_id}_{uuid.uuid4().hex[:6]}{ext}"
    dest = settings.audio_dir / filename

    content = await file.read()
    dest.write_bytes(content)

    from app.services.audio_service import audio_service

    dur = audio_service.get_audio_duration(str(dest))

    track = AudioTrack(
        episode_id=episode_id,
        track_type=track_type,
        name=name,
        file_path=f"/media/audio/{filename}",
        duration_seconds=dur,
        volume=0.3 if track_type == "music" else 1.0,
        start_time=0.0,
        status="ready",
    )
    session.add(track)
    session.commit()
    session.refresh(track)
    return track


@router.put("/{track_id}", response_model=AudioTrackResponse)
async def update_audio_track(
    episode_id: str,
    track_id: str,
    data: AudioTrackUpdate,
    session: Session = Depends(get_session),
):
    """Pas volume of timing van een audiotrack aan."""
    track = session.get(AudioTrack, track_id)
    if not track or track.episode_id != episode_id:
        raise HTTPException(status_code=404, detail="Audiotrack niet gevonden.")

    update_dict = data.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        if hasattr(track, k) and v is not None:
            setattr(track, k, v)

    session.add(track)
    session.commit()
    session.refresh(track)
    return track


@router.delete("/{track_id}")
async def delete_audio_track(
    episode_id: str,
    track_id: str,
    session: Session = Depends(get_session),
):
    """Verwijder een audiotrack."""
    track = session.get(AudioTrack, track_id)
    if not track or track.episode_id != episode_id:
        raise HTTPException(status_code=404, detail="Audiotrack niet gevonden.")
    session.delete(track)
    session.commit()
    return {"detail": "Audiotrack verwijderd."}

