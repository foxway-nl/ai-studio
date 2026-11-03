"""Settings Manager – lees/schrijf key-value instellingen naar de database.

Wordt gebruikt door het Setup Centrum om API-sleutels en service-URL's op te slaan
en op te halen zonder herstart van de applicatie.
"""

from typing import Optional

from sqlmodel import Session, select

from app.models.models import AppSetting
from .database import get_engine


class SettingsManager:
    """Beheer applicatie-instellingen in de database."""

    @staticmethod
    def get(key: str, default: Optional[str] = None) -> Optional[str]:
        """Haal een instelling op uit de database."""
        engine = get_engine()
        with Session(engine) as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            setting = session.exec(stmt).first()
            if setting is not None:
                return setting.value
            return default

    @staticmethod
    def set(key: str, value: str, description: str = "") -> None:
        """Sla een instelling op in de database (insert of update)."""
        engine = get_engine()
        with Session(engine) as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            setting = session.exec(stmt).first()
            if setting is not None:
                setting.value = value
                if description:
                    setting.description = description
            else:
                setting = AppSetting(key=key, value=value, description=description)
                session.add(setting)
            session.commit()

    @staticmethod
    def get_all() -> dict[str, str]:
        """Haal alle instellingen op als dictionary."""
        engine = get_engine()
        with Session(engine) as session:
            settings = session.exec(select(AppSetting)).all()
            return {s.key: s.value for s in settings}

    @staticmethod
    def delete(key: str) -> bool:
        """Verwijder een instelling uit de database."""
        engine = get_engine()
        with Session(engine) as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            setting = session.exec(stmt).first()
            if setting is not None:
                session.delete(setting)
                session.commit()
                return True
            return False

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

