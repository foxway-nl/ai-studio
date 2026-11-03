"""SQLite database engine en sessie management via SQLModel."""

from sqlmodel import Session, SQLModel, create_engine

from .config import settings

_engine = None


def get_engine():
    """Lazy-initialize de database engine (SQLite, single-file)."""
    global _engine
    if _engine is None:
        connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.database_url,
            echo=False,
            connect_args=connect_args,
        )
    return _engine


def init_db() -> None:
    """Maak alle tabellen aan als ze nog niet bestaan."""
    from app.models import models as _  # noqa: F401 – registreer tabellen

    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """Yield een database sessie voor dependency injection."""
    engine = get_engine()
    with Session(engine) as session:
        yield session

