"""Envío de correos vía SMTP (mismas credenciales que IMAP)."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from email.utils import formatdate, make_msgid


class SmtpError(Exception):
    pass


@dataclass
class SmtpSettings:
    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False


def enviar_correo_smtp(
    settings: SmtpSettings,
    destinatario: str,
    asunto: str,
    cuerpo: str,
) -> bytes:
    mode = "SSL" if settings.use_ssl else ("STARTTLS" if settings.use_tls else "sin cifrado")
    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = settings.username
    msg["To"] = destinatario
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=(settings.username.split("@")[-1] or None))
    msg.set_content(cuerpo)

    try:
        smtp_class = smtplib.SMTP_SSL if settings.use_ssl else smtplib.SMTP
        with smtp_class(settings.host, settings.port, timeout=60) as smtp:
            if not settings.use_ssl:
                smtp.ehlo()
                if settings.use_tls:
                    smtp.starttls()
                    smtp.ehlo()
            smtp.login(settings.username, settings.password)
            smtp.send_message(msg)
            return msg.as_bytes()
    except smtplib.SMTPAuthenticationError as exc:
        raise SmtpError(
            f"Error de autenticación SMTP ({settings.host}:{settings.port}, {mode}): {exc}"
        ) from exc
    except smtplib.SMTPException as exc:
        raise SmtpError(
            f"Error al enviar el correo por SMTP ({settings.host}:{settings.port}, {mode}): {exc}"
        ) from exc
    except OSError as exc:
        raise SmtpError(f"No se pudo conectar a {settings.host}:{settings.port} ({mode}): {exc}") from exc
