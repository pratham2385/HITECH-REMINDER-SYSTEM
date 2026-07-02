"""Database engine and session helpers."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.config.settings import PROJECT_ROOT, Settings, load_settings
from src.db.models import Base, User
from src.security import hash_password


_engine = None
_session_factory: sessionmaker[Session] | None = None


def normalize_database_url(database_url: str) -> str:
    """Resolve a relative SQLite URL against the project root."""

    prefix = "sqlite:///"
    if database_url.startswith(prefix) and not database_url.startswith("sqlite:////"):
        raw_path = database_url[len(prefix) :]
        path = Path(raw_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{path.as_posix()}"
    return database_url


def get_engine(settings: Settings | None = None):
    """Return the configured SQLAlchemy engine."""

    global _engine
    if _engine is None:
        active_settings = settings or load_settings()
        database_url = normalize_database_url(active_settings.database_url)
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        _engine = create_engine(database_url, connect_args=connect_args, future=True)
    return _engine


def get_session_factory(settings: Settings | None = None) -> sessionmaker[Session]:
    """Return the configured session factory."""

    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(settings),
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _session_factory


@contextmanager
def db_session(settings: Settings | None = None) -> Iterator[Session]:
    """Provide a transactional database session."""

    session = get_session_factory(settings)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database(settings: Settings | None = None) -> None:
    """Create tables and seed the default owner account when needed."""

    active_settings = settings or load_settings()
    Base.metadata.create_all(bind=get_engine(active_settings))

    with db_session(active_settings) as session:
        existing_user = session.query(User).first()
        if existing_user:
            return

        session.add(
            User(
                username=active_settings.dashboard_admin_username,
                display_name="Owner",
                password_hash=hash_password(active_settings.dashboard_admin_password),
                role="owner",
                is_active=True,
            )
        )

