import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
OBJETOS_DIR = Path(r"C:\Users\Andres\Source\Python\Objetos")
INCIDENCIAS_DIR = Path(r"C:\Users\Andres\Source\Python\Incidencias")
PRESENCIA_DIR = Path(r"C:\Users\Andres\Source\Python\ControldePresencia")

load_dotenv(BASE_DIR / ".env")
load_dotenv(OBJETOS_DIR / ".env", override=False)
load_dotenv(PRESENCIA_DIR / ".env", override=False)


def _read_env_file(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == key:
            return value.strip().strip('"').strip("'")
    return ""


def _load_presencia_db_name() -> str:
    explicit = os.getenv("PRESENCIA_DB_NAME", "").strip()
    if explicit:
        return explicit
    from_file = _read_env_file(PRESENCIA_DIR / ".env", "DB_NAME")
    return from_file or "ControldePresencia"


def _load_secret_key() -> str:
    explicit = os.getenv("SECRET_KEY", "").strip()
    if explicit:
        return explicit
    from_file = _read_env_file(PRESENCIA_DIR / ".env", "SECRET_KEY")
    return from_file or "cambia-esto-en-produccion"


def _load_bc_credentials() -> tuple[str, str]:
    user = os.getenv("BC_USERNAME", "").strip()
    password = os.getenv("BC_PASSWORD", "")
    if user and password:
        return user, password
    try:
        import sys

        if str(INCIDENCIAS_DIR) not in sys.path:
            sys.path.insert(0, str(INCIDENCIAS_DIR))
        from config import BC_CONFIG  # type: ignore[import-not-found]

        creds = BC_CONFIG.get("credentials", {})
        return str(creds.get("username", "")).strip(), str(creds.get("password", ""))
    except Exception:
        return "", ""


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "si", "sí"}


class Settings:
    db_server: str = os.getenv("DB_SERVER", "localhost").strip()
    db_name: str = os.getenv("ESTUDIO_DB_NAME", os.getenv("DB_NAME", "Estudio")).strip()
    db_user: str = os.getenv("DB_USER", "").strip()
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server").strip().replace("+", " ")
    db_trusted_connection: bool = _env_bool("DB_TRUSTED_CONNECTION")

    bc_base_url: str = os.getenv("BC_BASE_URL", "https://bc220.malla.es").rstrip("/")
    bc_company: str = os.getenv("BC_COMPANY", "Malla Publicidad").strip()
    bc_timeout: int = int(os.getenv("BC_TIMEOUT", "60"))
    bc_username: str
    bc_password: str

    strapi_url: str = os.getenv("STRAPI_URL", "https://base64-api.deploy.malla.es").rstrip("/")
    host: str = os.getenv("HOST", os.getenv("FLASK_HOST", "127.0.0.1"))
    port: int = int(os.getenv("PORT", os.getenv("FLASK_PORT", "8000")))
    flask_debug: bool = _env_bool("FLASK_DEBUG")
    secret_key: str = _load_secret_key()
    presencia_db_name: str = _load_presencia_db_name()

    schema_path: Path = Path(
        os.getenv(
            "ESTUDIO_SCHEMA_PATH",
            OBJETOS_DIR / "sql" / "estudio_schema.sql",
        )
    )

    def pyodbc_connection_string(self, database: str | None = None) -> str:
        parts = [
            f"DRIVER={{{self.db_driver}}}",
            f"SERVER={self.db_server}",
            f"DATABASE={database or self.db_name}",
            "TrustServerCertificate=yes",
        ]
        if self.db_trusted_connection:
            parts.append("Trusted_Connection=yes")
        else:
            parts.extend([f"UID={self.db_user}", f"PWD={self.db_password}"])
        return ";".join(parts)

    def sqlalchemy_database_uri(self) -> str:
        driver = quote_plus(self.db_driver)
        if self.db_trusted_connection:
            return (
                f"mssql+pyodbc://@{self.db_server}/{self.db_name}"
                f"?driver={driver}&trusted_connection=yes&TrustServerCertificate=yes"
            )
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"mssql+pyodbc://{user}:{password}@{self.db_server}/{self.db_name}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )

    def presencia_database_uri(self) -> str:
        driver = quote_plus(self.db_driver)
        if self.db_trusted_connection:
            return (
                f"mssql+pyodbc://@{self.db_server}/{self.presencia_db_name}"
                f"?driver={driver}&trusted_connection=yes&TrustServerCertificate=yes"
            )
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"mssql+pyodbc://{user}:{password}@{self.db_server}/{self.presencia_db_name}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )


settings = Settings()
settings.bc_username, settings.bc_password = _load_bc_credentials()
