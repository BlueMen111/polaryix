from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config.settings import settings


class Base(DeclarativeBase):
    pass


def get_database_url() -> str:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL nao configurado.")
    return settings.database_url


def is_database_enabled() -> bool:
    return bool(settings.database_url and "DIGITE_A_SENHA_AQUI" not in settings.database_url and "SENHA_FORTE" not in settings.database_url)


engine = create_engine(
    get_database_url(),
    echo=settings.database_echo,
    pool_pre_ping=True,
    future=True,
) if is_database_enabled() else None

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True) if engine else None


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError("DATABASE_URL nao configurado.")
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_database_schema() -> None:
    if engine is None:
        raise RuntimeError("DATABASE_URL nao configurado.")
    from app.core import db_models  # noqa: F401

    Base.metadata.create_all(bind=engine)
