"""YouTube Data API v3 OAuth2 & Resumable Upload service voor AI-Studio.

Ondersteunt:
- OAuth2 flow (autorisatie URL, callback uitwisseling, tokenopslag)
- Live kanaal info & avatar ophalen
- Resumable video upload met status & voortgang
- Keuze tussen Mode A (Kids / COPPA `selfDeclaredMadeForKids=True`) en Mode B (Algemeen `selfDeclaredMadeForKids=False`)
- Automatische thumbnail upload en metadata beheer
"""

import json
import logging
import os
from typing import Any, Callable, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import settings
from app.core.settings_manager import settings_manager

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/youtube.readonly",
]


class YouTubeService:
    """Service voor YouTube Data API v3 interactie."""

    def __init__(self):
        pass

    def _get_client_config(self) -> Dict[str, Any]:
        """Haal OAuth2 client configuratie op uit de settings database."""
        client_id = settings_manager.get("youtube_client_id", settings.youtube_client_id).strip()
        client_secret = settings_manager.get("youtube_client_secret", settings.youtube_client_secret).strip()
        if not client_id or not client_secret:
            raise ValueError(
                "YouTube Client ID en Secret zijn niet ingesteld. "
                "Configureer deze in het Setup Centrum."
            )
        return {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        }

    def get_auth_url(self, redirect_uri: str = "http://localhost:3000/render/callback") -> str:
        """Genereer de Google OAuth2 login URL."""
        client_config = self._get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code(self, code: str, redirect_uri: str = "http://localhost:3000/render/callback") -> Dict[str, Any]:
        """Wissel de OAuth2 auth-code in voor tokens en sla ze op."""
        client_config = self._get_client_config()
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials

        token_info = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": creds.scopes,
        }
        settings_manager.set("youtube_oauth_token", json.dumps(token_info), "YouTube OAuth tokens")
        return {"status": "connected"}

    def get_credentials(self) -> Optional[Credentials]:
        """Laad opgeslagen credentials en refresh indien nodig."""
        token_str = settings_manager.get("youtube_oauth_token")
        if not token_str:
            return None
        try:
            data = json.loads(token_str)
            creds = Credentials(
                token=data.get("token"),
                refresh_token=data.get("refresh_token"),
                token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=data.get("client_id"),
                client_secret=data.get("client_secret"),
                scopes=data.get("scopes", SCOPES),
            )
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
                data["token"] = creds.token
                settings_manager.set("youtube_oauth_token", json.dumps(data))
            return creds
        except Exception as e:
            logger.error("Fout bij laden YouTube credentials: %s", e)
            return None

    def get_channel_info(self) -> Optional[Dict[str, Any]]:
        """Haal profiel en kanaalstatistieken op van het actieve gekoppelde account."""
        creds = self.get_credentials()
        if not creds:
            return None
        try:
            youtube = build("youtube", "v3", credentials=creds)
            res = youtube.channels().list(part="snippet,statistics", mine=True).execute()
            items = res.get("items", [])
            if not items:
                return None
            ch = items[0]
            snippet = ch.get("snippet", {})
            stats = ch.get("statistics", {})
            thumbs = snippet.get("thumbnails", {})
            avatar_url = (
                thumbs.get("default", {}).get("url")
                or thumbs.get("medium", {}).get("url")
                or ""
            )
            return {
                "connected": True,
                "id": ch.get("id"),
                "title": snippet.get("title", "Gekoppeld YouTube Kanaal"),
                "description": snippet.get("description", ""),
                "custom_url": snippet.get("customUrl", ""),
                "avatar_url": avatar_url,
                "subscriber_count": stats.get("subscriberCount", "0"),
                "video_count": stats.get("videoCount", "0"),
            }
        except Exception as e:
            logger.warning("Fout bij ophalen YouTube kanaal info: %s", e)
            return None

    def disconnect(self) -> None:
        """Verwijder de gekoppelde YouTube OAuth sessie."""
        settings_manager.delete("youtube_oauth_token")

    def upload_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: Optional[List[str]] = None,
        category_id: str = "27",  # Education category
        privacy_status: str = "private",
        made_for_kids: bool = True,
        progress_callback: Optional[Callable[[float, str], None]] = None,
    ) -> Dict[str, Any]:
        """Upload video via resumable upload met Made for Kids markering."""
        creds = self.get_credentials()
        if not creds:
            raise RuntimeError("Niet geauthenticeerd bij YouTube. Koppel eerst je kanaal.")

        youtube = build("youtube", "v3", credentials=creds)

        body = {
            "snippet": {
                "title": title[:100],
                "description": description[:5000],
                "tags": tags or ["kinderen", "educatief", "leren"],
                "categoryId": category_id,
            },
            "status": {
                "privacyStatus": privacy_status,
                # COPPA verplichting voor virale kindervideo's of standaard video:
                "selfDeclaredMadeForKids": bool(made_for_kids),
            },
        }

        media = MediaFileUpload(
            video_path,
            chunksize=1024 * 1024 * 5,  # 5MB chunks
            resumable=True,
            mimetype="video/mp4",
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status and progress_callback:
                progress_callback(status.progress(), f"Uploaden: {int(status.progress() * 100)}%")

        video_id = response.get("id")
        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if progress_callback:
            progress_callback(1.0, f"Gepubliceerd: {video_url}")

        return {
            "video_id": video_id,
            "url": video_url,
            "status": response.get("status", {}).get("uploadStatus", "uploaded"),
        }

    def set_thumbnail(self, video_id: str, thumbnail_path: str) -> None:
        """Upload een custom thumbnail voor een video."""
        creds = self.get_credentials()
        if not creds:
            return
        try:
            youtube = build("youtube", "v3", credentials=creds)
            media = MediaFileUpload(thumbnail_path, mimetype="image/png")
            youtube.thumbnails().set(videoId=video_id, media_body=media).execute()
        except Exception as e:
            logger.warning("Fout bij instellen thumbnail: %s", e)

    def get_upload_status(self, video_id: str) -> Dict[str, Any]:
        """Haal status op van een geüploade video."""
        creds = self.get_credentials()
        if not creds:
            return {"status": "unauthenticated"}
        youtube = build("youtube", "v3", credentials=creds)
        res = youtube.videos().list(part="status,snippet", id=video_id).execute()
        items = res.get("items", [])
        if not items:
            return {"status": "not_found"}
        return items[0]


youtube_service = YouTubeService()
