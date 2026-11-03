"""Settings Manager – lees/schrijf key-value instellingen naar de database en /data/config.json.

Wordt gebruikt door het Setup Centrum om API-sleutels en service-URL's op te slaan
en op te halen zonder herstart van de applicatie.
"""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from sqlmodel import Session, select

from app.models.models import AppSetting
from .database import get_engine

logger = logging.getLogger(__name__)


def _get_config_json_path() -> Path:
    data_dir = os.getenv("DATA_DIR", "/data")
    p = Path(data_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p / "config.json"


def _read_config_json() -> dict[str, str]:
    try:
        path = _get_config_json_path()
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        logger.debug("Kon config.json niet lezen: %s", e)
    return {}


def _write_config_json(data: dict[str, str]) -> None:
    try:
        path = _get_config_json_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning("Kon config.json niet schrijven: %s", e)


class SettingsManager:
    """Beheer applicatie-instellingen in SQLite en /data/config.json."""

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """Haal een instelling op uit de database of config.json."""
        k = key.strip()
        try:
            engine = get_engine()
            with Session(engine) as session:
                stmt = select(AppSetting).where(AppSetting.key == k)
                setting = session.exec(stmt).first()
                if setting is not None and setting.value is not None:
                    val = str(setting.value).strip()
                    if val:
                        return val
        except Exception as e:
            logger.debug("Database get error voor %s: %s", k, e)

        # Fallback naar config.json
        cfg = _read_config_json()
        if k in cfg and cfg[k] is not None:
            val = str(cfg[k]).strip()
            if val:
                return val

        if default is not None:
            return str(default).strip()
        return None

    @staticmethod
    def is_masked_value(value: Optional[str]) -> bool:
        """Controleer of een waarde gemaskeerd is (sterretjes, bullets, etc.)."""
        if not value:
            return False
        v = str(value).strip()
        if any(c in v for c in ("•", "●", "·", "…")):
            return True
        if "****" in v or "***" in v:
            return True
        return False

    @staticmethod
    def set(key: str, value: str, description: str = "") -> None:
        """Sla een instelling op in de database en sync naar config.json.
        Gemaskeerde waarden (••• of ****) overschrijven NOOIT een bestaande echte sleutel!
        """
        k = key.strip()
        v = str(value).strip().strip('"').strip("'") if value is not None else ""

        # Bescherm gevoelige API-sleutels tegen per ongeluk overschrijven met maskers
        if SettingsManager.is_masked_value(v):
            existing = SettingsManager.get(k)
            if existing and not SettingsManager.is_masked_value(existing):
                logger.info("Setting %s behoudt bestaande echte waarde; gemaskeerde invoer genegeerd.", k)
                return

        # Sla op in SQLite
        try:
            engine = get_engine()
            with Session(engine) as session:
                stmt = select(AppSetting).where(AppSetting.key == k)
                setting = session.exec(stmt).first()
                if setting is not None:
                    setting.value = v
                    if description:
                        setting.description = description
                else:
                    setting = AppSetting(key=k, value=v, description=description)
                    session.add(setting)
                session.commit()
        except Exception as e:
            logger.warning("Fout bij opslaan setting %s in database: %s", k, e)

        # Sync naar config.json
        cfg = _read_config_json()
        cfg[k] = v
        _write_config_json(cfg)

    @staticmethod
    def get_all() -> dict[str, str]:
        """Haal alle instellingen op als dictionary."""
        results = _read_config_json()
        try:
            engine = get_engine()
            with Session(engine) as session:
                settings_list = session.exec(select(AppSetting)).all()
                for s in settings_list:
                    if s.key and s.value is not None:
                        results[s.key.strip()] = str(s.value).strip()
        except Exception as e:
            logger.debug("Fout bij ophalen alle settings uit DB: %s", e)
        return results

    @staticmethod
    def delete(key: str) -> bool:
        """Verwijder een instelling uit de database en config.json."""
        k = key.strip()
        deleted = False
        try:
            engine = get_engine()
            with Session(engine) as session:
                stmt = select(AppSetting).where(AppSetting.key == k)
                setting = session.exec(stmt).first()
                if setting is not None:
                    session.delete(setting)
                    session.commit()
                    deleted = True
        except Exception:
            pass

        cfg = _read_config_json()
        if k in cfg:
            del cfg[k]
            _write_config_json(cfg)
            deleted = True

        return deleted

    @staticmethod
    def get_masked(key: str) -> Optional[str]:
        """Haal een instelling op met gemaskeerde waarde (voor weergave in UI)."""
        value = SettingsManager.get(key)
        if value is None or len(value) == 0:
            return None
        if len(value) <= 8:
            return "****"
        return value[:4] + "****" + value[-4:]


settings_manager = SettingsManager()
