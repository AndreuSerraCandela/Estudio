"""Envío de correos vía SMTP (mismas credenciales que IMAP)."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


class SmtpError(Exception):
    pass


@dataclass
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True


def enviar_correo_smtp(
    settings: SmtpSettings,
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = settings.username
    msg["To"] = destinatario
    msg.set_content(cuerpo)

    try:
        with smtplib.SMTP(settings.host, settings.port, timeout=60) as smtp:
            smtp.ehlo()
            if settings.use_tls:
                smtp.starttls()
                smtp.ehlo()
            smtp.login(settings.username, settings.password)
            smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        raise SmtpError(f"Error de autenticación SMTP: {exc}") from exc
    except smtplib.SMTPException as exc:
        raise SmtpError(f"Error al enviar el correo: {exc}") from exc
    except OSError as exc:
        raise SmtpError(f"No se pudo conectar a {settings.host}:{settings.port}: {exc}") from exc
