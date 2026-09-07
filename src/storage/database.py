"""SQLite engine, session, and migration helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic.config import Config
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from alembic import command

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_PATH = Path("data/monitor.db")


def sqlite_url(database_path: str | Path = DEFAULT_DATABASE_PATH) -> str:
    """Build a SQLite URL for a filesystem database path."""

    return f"sqlite:///{Path(database_path)}"


def create_sqlite_engine(
    database_path: str | Path = DEFAULT_DATABASE_PATH,
    *,
    echo: bool = False,
) -> Engine:
    """Create a SQLite engine with project-required PRAGMAs."""

    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(sqlite_url(path), echo=echo, future=True)
    _configure_sqlite_pragmas(engine)
    return engine


def session_factory(engine: Engine) -> sessionmaker[Session]:
    """Return a typed SQLAlchemy session factory."""

    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations."""

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def run_migrations(database_path: str | Path = DEFAULT_DATABASE_PATH) -> None:
    """Upgrade the configured SQLite database to the latest Alembic revision."""

    config = Config(PROJECT_ROOT / "alembic.ini")
    config.set_main_option("script_location", str(PROJECT_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", sqlite_url(database_path))
    engine = create_sqlite_engine(database_path)
    try:
        with engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
    finally:
        engine.dispose()


def _configure_sqlite_pragmas(engine: Engine) -> None:
    url = make_url(str(engine.url))
    if url.drivername != "sqlite":
        raise ValueError("Forum Scraper storage only supports SQLite")

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # type: ignore[no-untyped-def]
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()
