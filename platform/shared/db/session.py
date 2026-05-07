from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from shared.config.settings import settings

engine = create_engine(settings.postgres_dsn)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_engine_and_session():
    """Return (engine, SessionLocal) for use outside of FastAPI request context.

    Celery tasks call this instead of using the FastAPI dependency injection
    system (which is not available outside of request handling).
    """
    return engine, SessionLocal
