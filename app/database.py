from pathlib import Path

import pyodbc
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


def _validate_database_name(name: str) -> str:
    if not name or not all(char.isalnum() or char in ("_", "-") for char in name):
        raise ValueError(f"Nombre de base de datos no válido: {name!r}")
    return name


def ensure_database() -> None:
    if not settings.auto_create_database:
        return

    database = _validate_database_name(settings.db_name)
    with pyodbc.connect(settings.pyodbc_connection_string("master"), autocommit=True) as conn:
        cursor = conn.cursor()
        if cursor.execute("SELECT DB_ID(?)", database).fetchone()[0] is None:
            cursor.execute(f"CREATE DATABASE [{database}]")


def _run_schema_script() -> None:
    schema_path = Path(settings.schema_path)
    if not schema_path.is_file():
        raise FileNotFoundError(
            f"No se encontró el esquema SQL: {schema_path}. "
            "Copia sql/estudio_schema.sql al servidor o define ESTUDIO_SCHEMA_PATH en .env"
        )

    sql = schema_path.read_text(encoding="utf-8")
    with pyodbc.connect(settings.pyodbc_connection_string(), autocommit=True) as conn:
        cursor = conn.cursor()
        cursor.execute(sql)


engine = create_engine(
    settings.sqlalchemy_database_uri(),
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    ensure_database()
    _run_schema_script()
