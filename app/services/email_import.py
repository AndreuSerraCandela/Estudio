"""Importación de correos desde archivos .eml (multiplataforma)."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path


@dataclass
class ImportedMailInfo:
    direccion: str
    asunto: str
    destinatario: str | None
    remitente: str | None
    fecha: datetime | None
    conversation_id: str | None
    outlook_entry_id: str | None
    internet_message_id: str | None
    file_bytes: bytes
    nombre_archivo: str
    mime_type: str


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    return str(value).strip()


def _addresses(header_value: str | None) -> str:
    if not header_value:
        return ""
    parts = [addr for _, addr in getaddresses([header_value]) if addr]
    return ", ".join(parts)


def _parse_fecha(msg) -> datetime | None:
    for header in ("Date", "Delivery-Date"):
        raw = msg.get(header)
        if not raw:
            continue
        try:
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        except (TypeError, ValueError, IndexError):
            continue
    return None


def _infer_direccion(remitente: str, destinatario: str, usuario_email: str | None) -> str:
    if not usuario_email:
        return "recibido"
    email_norm = usuario_email.strip().lower()
    remitente_norm = remitente.lower()
    if email_norm and email_norm in remitente_norm:
        return "enviado"
    return "recibido"


def _unique_message_id(msg, content: bytes) -> str:
    raw = _decode_header(msg.get("Message-ID"))
    if raw:
        return raw
    digest = hashlib.sha256(content).hexdigest()
    return f"hash:{digest}"


def subject_marker(numero_expediente: str) -> str:
    safe = re.sub(r"[^\w\-./]", "", numero_expediente.strip())
    return f"[EXP-{safe}]"


def parse_eml_bytes(
    content: bytes,
    filename: str,
    *,
    direccion: str | None = None,
    usuario_email: str | None = None,
) -> ImportedMailInfo:
    msg = BytesParser(policy=policy.default).parsebytes(content)
    asunto = _decode_header(msg.get("Subject")) or "(sin asunto)"
    remitente = _addresses(msg.get("From"))
    destinatario = _addresses(msg.get("To"))
    if not destinatario:
        destinatario = _addresses(msg.get("Delivered-To")) or _addresses(msg.get("Cc"))

    if direccion not in ("enviado", "recibido"):
        direccion = _infer_direccion(remitente, destinatario, usuario_email)

    safe_name = re.sub(r'[<>:"/\\|?*]', "_", asunto)[:120] or "correo"
    ext = Path(filename).suffix.lower()
    nombre = filename if ext in {".eml", ".msg"} else f"{safe_name}.eml"

    return ImportedMailInfo(
        direccion=direccion,
        asunto=asunto,
        destinatario=destinatario or None,
        remitente=remitente or None,
        fecha=_parse_fecha(msg),
        conversation_id=_decode_header(msg.get("Thread-Index")) or None,
        outlook_entry_id=None,
        internet_message_id=_unique_message_id(msg, content),
        file_bytes=content,
        nombre_archivo=nombre,
        mime_type="message/rfc822",
    )
