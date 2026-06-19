"""Preferencias por usuario (BD Estudio, vinculadas a Control de Presencia)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import UsuarioConfig
from app.services.crypto_utils import decrypt_secret, encrypt_secret
from app.services.imap_sync import ImapSettings
from app.services.smtp_send import SmtpSettings

IMAP_DEFAULTS = {
    "host": "outlook.office365.com",
    "port": 993,
    "use_ssl": True,
    "carpeta_entrada": "INBOX",
    "carpeta_enviados": "Sent Items",
}

SMTP_DEFAULTS = {
    "host": "smtp.office365.com",
    "port": 587,
    "use_tls": True,
}


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
    imap_host = (config.imap_host or IMAP_DEFAULTS["host"]).strip().lower()
    if "office365" in imap_host or "outlook" in imap_host:
        smtp_host = SMTP_DEFAULTS["host"]
    else:
        smtp_host = imap_host.replace("imap.", "smtp.", 1) if imap_host.startswith("imap.") else imap_host
    return SmtpSettings(
        host=smtp_host,
        port=SMTP_DEFAULTS["port"],
        username=(config.imap_username or "").strip(),
        password=password,
        use_tls=SMTP_DEFAULTS["use_tls"],
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
) -> UsuarioConfig:
    config = get_usuario_config(db, presencia_user_id)
    config.imap_host = host.strip() or IMAP_DEFAULTS["host"]
    config.imap_port = port or IMAP_DEFAULTS["port"]
    config.imap_use_ssl = use_ssl
    config.imap_username = username.strip() or None
    config.imap_carpeta_entrada = carpeta_entrada.strip() or IMAP_DEFAULTS["carpeta_entrada"]
    config.imap_carpeta_enviados = carpeta_enviados.strip() or IMAP_DEFAULTS["carpeta_enviados"]
    if password:
        config.imap_password_enc = encrypt_secret(password)
    elif not config.imap_password_enc:
        raise ValueError("Indica la contraseña IMAP (o contraseña de aplicación)")
    config.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    db.refresh(config)
    return config
