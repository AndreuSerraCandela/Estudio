from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class PresenciaBase(DeclarativeBase):
    pass


presencia_engine = create_engine(
    settings.presencia_database_uri(),
    pool_pre_ping=True,
)
PresenciaSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=presencia_engine)


def get_presencia_db():
    db = PresenciaSessionLocal()
    try:
        yield db
    finally:
        db.close()
