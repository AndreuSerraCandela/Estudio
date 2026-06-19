import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

_DEV_OBJETOS_DIR = Path(r"C:\Users\Andres\Source\Python\Objetos")
_DEV_INCIDENCIAS_DIR = Path(r"C:\Users\Andres\Source\Python\Incidencias")
_DEV_PRESENCIA_DIR = Path(r"C:\Users\Andres\Source\Python\ControldePresencia")


def _optional_dir(env_name: str, dev_default: Path) -> Path | None:
    explicit = os.getenv(env_name, "").strip()
    if explicit:
        path = Path(explicit)
        return path if path.is_dir() else None
    return dev_default if dev_default.is_dir() else None


def _resolve_path(env_name: str, *candidates: Path) -> Path:
    explicit = os.getenv(env_name, "").strip()
    if explicit:
        return Path(explicit)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return candidates[0]


load_dotenv(BASE_DIR / ".env")

OBJETOS_DIR = _optional_dir("OBJETOS_DIR", _DEV_OBJETOS_DIR)
INCIDENCIAS_DIR = _optional_dir("INCIDENCIAS_DIR", _DEV_INCIDENCIAS_DIR)
PRESENCIA_DIR = _optional_dir("PRESENCIA_DIR", _DEV_PRESENCIA_DIR)

for extra_dir in (OBJETOS_DIR, PRESENCIA_DIR):
    if extra_dir is not None:
        load_dotenv(extra_dir / ".env", override=False)


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


def _presencia_env_candidates() -> list[Path]:
    explicit = os.getenv("PRESENCIA_ENV_FILE", "").strip()
    candidates = [
        Path(explicit) if explicit else None,
        Path(r"C:\inetpub\wwwroot\ControlPresencia\.env"),
        Path(r"C:\inetpub\wwwroot\ControldePresencia\.env"),
        PRESENCIA_DIR / ".env" if PRESENCIA_DIR else None,
    ]
    return [path for path in candidates if path is not None and path.is_file()]


for _presencia_env_path in _presencia_env_candidates():
    load_dotenv(_presencia_env_path, override=False)


def _presencia_env_value(key: str) -> str:
    for path in _presencia_env_candidates():
        value = _read_env_file(path, key)
        if value:
            return value
    return ""


def _setting_or_presencia_env(name: str, presencia_key: str, default: str = "") -> str:
    explicit = os.getenv(name, "").strip()
    if explicit:
        return explicit
    from_presencia = _presencia_env_value(presencia_key)
    if from_presencia:
        return from_presencia
    return default


def _load_presencia_db_name() -> str:
    name = _setting_or_presencia_env("PRESENCIA_DB_NAME", "DB_NAME", "ControlPresencia")
    # Typo habitual: la BD se llama ControlPresencia, no ControldePresencia
    if name.replace("_", "").lower() == "controldepresencia":
        return "ControlPresencia"
    return name


def _load_secret_key() -> str:
    explicit = os.getenv("SECRET_KEY", "").strip()
    if explicit:
        return explicit
    if PRESENCIA_DIR is not None:
        from_file = _read_env_file(PRESENCIA_DIR / ".env", "SECRET_KEY")
        if from_file:
            return from_file
    return "cambia-esto-en-produccion"


def _load_bc_credentials() -> tuple[str, str]:
    user = os.getenv("BC_USERNAME", "").strip()
    password = os.getenv("BC_PASSWORD", "")
    if user and password:
        return user, password
    if INCIDENCIAS_DIR is None:
        return "", ""
    try:
        incidencias_path = str(INCIDENCIAS_DIR)
        if incidencias_path not in sys.path:
            sys.path.insert(0, incidencias_path)
        from config import BC_CONFIG  # type: ignore[import-not-found]

        creds = BC_CONFIG.get("credentials", {})
        return str(creds.get("username", "")).strip(), str(creds.get("password", ""))
    except Exception:
        return "", ""


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "si", "sí"}


def _default_schema_path() -> Path:
    return _resolve_path(
        "ESTUDIO_SCHEMA_PATH",
        BASE_DIR / "sql" / "estudio_schema.sql",
        *([OBJETOS_DIR / "sql" / "estudio_schema.sql"] if OBJETOS_DIR else []),
    )


def _default_logo_path() -> Path:
    return _resolve_path(
        "CORPORATIVO_LOGO_PATH",
        BASE_DIR / "app" / "static" / "images" / "logomalla.png",
        *([PRESENCIA_DIR / "app" / "static" / "images" / "logomalla.png"] if PRESENCIA_DIR else []),
    )


class Settings:
    db_server: str = os.getenv("DB_SERVER", "localhost").strip()
    db_name: str = os.getenv("ESTUDIO_DB_NAME", os.getenv("DB_NAME", "Estudio")).strip()
    db_user: str = os.getenv("DB_USER", "").strip()
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server").strip().replace("+", " ")
    db_trusted_connection: bool = _env_bool("DB_TRUSTED_CONNECTION")
    auto_create_database: bool = _env_bool("ESTUDIO_AUTO_CREATE_DB", True)
    init_db_on_startup: bool = _env_bool("ESTUDIO_INIT_DB", True)

    bc_base_url: str = os.getenv("BC_BASE_URL", "https://bc220.malla.es").rstrip("/")
    bc_company: str = os.getenv("BC_COMPANY", "Malla Publicidad").strip()
    bc_timeout: int = int(os.getenv("BC_TIMEOUT", "60"))
    bc_username: str
    bc_password: str

    strapi_url: str = os.getenv("STRAPI_URL", "https://base64-api.deploy.malla.es").rstrip("/")
    host: str = os.getenv("HOST", os.getenv("FLASK_HOST", "127.0.0.1"))
    port: int = int(os.getenv("PORT", os.getenv("FLASK_PORT", "8000")))
    flask_debug: bool = _env_bool("FLASK_DEBUG")
    behind_https: bool = _env_bool("ESTUDIO_BEHIND_HTTPS", not _env_bool("FLASK_DEBUG"))
    secret_key: str = _load_secret_key()
    presencia_db_name: str = _load_presencia_db_name()
    presencia_db_server: str = _setting_or_presencia_env("PRESENCIA_DB_SERVER", "DB_SERVER", os.getenv("DB_SERVER", "localhost").strip())
    presencia_db_user: str = _setting_or_presencia_env("PRESENCIA_DB_USER", "DB_USER", os.getenv("DB_USER", "").strip())
    presencia_db_password: str = _setting_or_presencia_env("PRESENCIA_DB_PASSWORD", "DB_PASSWORD", os.getenv("DB_PASSWORD", ""))
    presencia_db_trusted_connection: bool = (
        _env_bool("PRESENCIA_DB_TRUSTED_CONNECTION")
        if os.getenv("PRESENCIA_DB_TRUSTED_CONNECTION", "").strip()
        else (
            _presencia_env_value("DB_TRUSTED_CONNECTION").lower() in {"1", "true", "yes", "si", "sí"}
            if _presencia_env_value("DB_TRUSTED_CONNECTION")
            else _env_bool("DB_TRUSTED_CONNECTION")
        )
    )

    schema_path: Path = _default_schema_path()
    corporativo_logo_path: Path = _default_logo_path()

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
        if self.presencia_db_trusted_connection:
            return (
                f"mssql+pyodbc://@{self.presencia_db_server}/{self.presencia_db_name}"
                f"?driver={driver}&trusted_connection=yes&TrustServerCertificate=yes"
            )
        user = quote_plus(self.presencia_db_user)
        password = quote_plus(self.presencia_db_password)
        return (
            f"mssql+pyodbc://{user}:{password}@{self.presencia_db_server}/{self.presencia_db_name}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )


settings = Settings()
settings.bc_username, settings.bc_password = _load_bc_credentials()
