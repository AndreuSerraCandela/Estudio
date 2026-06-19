"""Preferencias por usuario (BD Estudio, vinculadas a Control de Presencia)."""

from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import UsuarioConfig
from app.services.crypto_utils import decrypt_secret, encrypt_secret
from app.services.imap_sync import ImapSettings
from app.services.smtp_send import SmtpSettings


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name, "1" if default else "0").strip().lower()
    return value in {"1", "true", "yes", "si", "sí"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)).strip())
    except ValueError:
        return default


IMAP_DEFAULTS = {
    "host": os.getenv("ESTUDIO_IMAP_HOST", os.getenv("IMAP_HOST", "outlook.office365.com")).strip(),
    "port": _env_int("ESTUDIO_IMAP_PORT", _env_int("IMAP_PORT", 993)),
    "use_ssl": _env_bool("ESTUDIO_IMAP_USE_SSL", _env_bool("IMAP_USE_SSL", True)),
    "carpeta_entrada": os.getenv("ESTUDIO_IMAP_INBOX", os.getenv("IMAP_INBOX", "INBOX")).strip(),
    "carpeta_enviados": os.getenv("ESTUDIO_IMAP_SENT", os.getenv("IMAP_SENT", "Sent Items")).strip(),
}

SMTP_DEFAULTS = {
    "host": os.getenv("ESTUDIO_SMTP_HOST", os.getenv("MAIL_SERVER", "smtp.office365.com")).strip(),
    "port": _env_int("ESTUDIO_SMTP_PORT", _env_int("MAIL_PORT", 587)),
}
SMTP_DEFAULTS["use_ssl"] = _env_bool(
    "ESTUDIO_SMTP_USE_SSL",
    _env_bool("MAIL_USE_SSL", SMTP_DEFAULTS["port"] == 465),
)
SMTP_DEFAULTS["use_tls"] = _env_bool("ESTUDIO_SMTP_USE_TLS", not SMTP_DEFAULTS["use_ssl"])


def get_usuario_config(db: Session, presencia_user_id: int) -> UsuarioConfig:
    config = (
        db.query(UsuarioConfig)
        .filter(UsuarioConfig.presencia_user_id == presencia_user_id)
        .first()
    )
    if config is None:
        config = UsuarioConfig(
            presencia_user_id=presencia_user_id,
            imap_host=IMAP_DEFAULTS["host"],
            imap_port=IMAP_DEFAULTS["port"],
            imap_use_ssl=IMAP_DEFAULTS["use_ssl"],
            imap_carpeta_entrada=IMAP_DEFAULTS["carpeta_entrada"],
            imap_carpeta_enviados=IMAP_DEFAULTS["carpeta_enviados"],
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def imap_configurado(config: UsuarioConfig) -> bool:
    return bool(
        (config.imap_host or "").strip()
        and (config.imap_username or "").strip()
        and (config.imap_password_enc or "").strip()
    )


def imap_settings_from_config(config: UsuarioConfig) -> ImapSettings | None:
    if not imap_configurado(config):
        return None
    password = decrypt_secret(config.imap_password_enc)
    if not password:
        return None
    return ImapSettings(
        host=(config.imap_host or IMAP_DEFAULTS["host"]).strip(),
        port=int(config.imap_port or IMAP_DEFAULTS["port"]),
        use_ssl=bool(config.imap_use_ssl),
        username=(config.imap_username or "").strip(),
        password=password,
        carpeta_entrada=(config.imap_carpeta_entrada or IMAP_DEFAULTS["carpeta_entrada"]).strip(),
        carpeta_enviados=(config.imap_carpeta_enviados or IMAP_DEFAULTS["carpeta_enviados"]).strip(),
    )


def smtp_settings_from_config(config: UsuarioConfig) -> SmtpSettings | None:
    if not imap_configurado(config):
        return None
    password = decrypt_secret(config.imap_password_enc)
    if not password:
        return None
    imap_host = (config.imap_host or IMAP_DEFAULTS["host"]).strip()
    imap_host_lower = imap_host.lower()
    if (config.smtp_host or "").strip():
        smtp_host = (config.smtp_host or "").strip()
    elif "office365" in imap_host_lower or "outlook" in imap_host_lower:
        smtp_host = SMTP_DEFAULTS["host"]
    else:
        smtp_host = imap_host.replace("imap.", "smtp.", 1) if imap_host_lower.startswith("imap.") else imap_host
    smtp_port = int(config.smtp_port or SMTP_DEFAULTS["port"])
    use_ssl = bool(config.smtp_use_ssl)
    use_tls = bool(config.smtp_use_tls)
    if not (config.smtp_host or "").strip() and not config.smtp_port:
        use_ssl = bool(SMTP_DEFAULTS["use_ssl"])
        use_tls = bool(SMTP_DEFAULTS["use_tls"])
    elif smtp_port == 465 and not use_ssl:
        use_ssl = True
        use_tls = False
    elif smtp_port == 587 and use_ssl:
        use_ssl = False
        use_tls = True

    return SmtpSettings(
        host=smtp_host,
        port=smtp_port,
        username=(config.imap_username or "").strip(),
        password=password,
        use_tls=use_tls,
        use_ssl=use_ssl,
    )


def set_imap_config(
    db: Session,
    presencia_user_id: int,
    *,
    host: str,
    port: int,
    use_ssl: bool,
    username: str,
    password: str | None,
    carpeta_entrada: str,
    carpeta_enviados: str,
    guardar_copia_enviados: bool = False,
    smtp_host: str | None = None,
    smtp_port: int | None = None,
    smtp_use_tls: bool = True,
    smtp_use_ssl: bool = False,
) -> UsuarioConfig:
    config = get_usuario_config(db, presencia_user_id)
    config.imap_host = host.strip() or IMAP_DEFAULTS["host"]
    config.imap_port = port or IMAP_DEFAULTS["port"]
    config.imap_use_ssl = use_ssl
    config.imap_username = username.strip() or None
    config.imap_carpeta_entrada = carpeta_entrada.strip() or IMAP_DEFAULTS["carpeta_entrada"]
    config.imap_carpeta_enviados = carpeta_enviados.strip() or IMAP_DEFAULTS["carpeta_enviados"]
    config.imap_guardar_copia_enviados = bool(guardar_copia_enviados)
    config.smtp_host = (smtp_host or "").strip() or None
    config.smtp_port = smtp_port or None
    config.smtp_use_tls = bool(smtp_use_tls)
    config.smtp_use_ssl = bool(smtp_use_ssl)
    if password:
        config.imap_password_enc = encrypt_secret(password)
    elif not config.imap_password_enc:
        raise ValueError("Indica la contraseña IMAP (o contraseña de aplicación)")
    config.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(config)
    return config
