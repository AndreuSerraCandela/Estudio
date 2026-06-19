"""Visualización de correos .eml con extracción del cuerpo y citas."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from email import policy
from email.message import Message
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime


@dataclass
class EmailAttachmentInfo:
    nombre: str
    content_type: str
    size: int


@dataclass
class EmailView:
    asunto: str
    remitente: str
    destinatario: str
    cc: str
    fecha: str | None
    cuerpo_html: str | None
    cuerpo_texto: str | None
    cita_html: str | None
    cita_texto: str | None
    es_respuesta: bool
    adjuntos: list[EmailAttachmentInfo] = field(default_factory=list)


REPLY_PLAIN_PATTERNS = [
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}\s*$", re.I | re.M),
    re.compile(r"^\s*_{5,}\s*$", re.M),
    re.compile(r"^\s*From:\s.+?\n\s*Sent:\s", re.I | re.M),
    re.compile(r"^\s*De:\s.+?\n\s*Enviado(?: el)?:\s", re.I | re.M),
    re.compile(r"^\s*El .+ escribió:\s*$", re.I | re.M),
    re.compile(r"^\s*On .+ wrote:\s*$", re.I | re.M),
    re.compile(r"^\s*>{1,}\s", re.M),
]

REPLY_HTML_PATTERNS = [
    re.compile(r'<div[^>]+id=["\']divRplyFwdMsg["\']', re.I),
    re.compile(r"<blockquote\b", re.I),
    re.compile(r"<!--\s*Original Message\s-->", re.I),
    re.compile(r"^\s*-{2,}\s*Original Message\s*-{2,}", re.I | re.M),
]


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    return str(value).strip()


def _addresses(header_value: str | None) -> str:
    if not header_value:
        return ""
    parts = [addr for _, addr in getaddresses([header_value]) if addr]
    return ", ".join(parts)


def _format_fecha(msg: Message) -> str | None:
    raw = msg.get("Date")
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt.tzinfo is not None:
            dt = dt.replace(tzinfo=None)
        return dt.strftime("%d/%m/%Y %H:%M")
    except (TypeError, ValueError, IndexError):
        return _decode_header(raw) or None


def _unwrap_message(msg: Message) -> Message:
    while msg.get_content_type() == "message/rfc822":
        payload = msg.get_payload()
        if isinstance(payload, list) and payload:
            msg = payload[0]
            continue
        if isinstance(payload, Message):
            msg = payload
            continue
        break
    return msg


def _sanitize_html(raw: str) -> str:
    cleaned = re.sub(r"(?is)<script[^>]*>.*?</script>", "", raw)
    cleaned = re.sub(r"(?is)<style[^>]*>.*?</style>", "", cleaned)
    cleaned = re.sub(r'(?i)\son\w+\s*=\s*"[^"]*"', "", cleaned)
    cleaned = re.sub(r"(?i)\son\w+\s*=\s*'[^']*'", "", cleaned)
    return cleaned.strip()


def _split_plain_reply(text: str) -> tuple[str, str | None]:
    earliest = None
    for pattern in REPLY_PLAIN_PATTERNS:
        match = pattern.search(text)
        if match and (earliest is None or match.start() < earliest.start()):
            earliest = match
    if earliest is None:
        return text.strip(), None
    main = text[: earliest.start()].strip()
    quoted = text[earliest.start() :].strip()
    if not main:
        return text.strip(), None
    return main, quoted or None


def _split_html_reply(html: str) -> tuple[str, str | None]:
    earliest = None
    for pattern in REPLY_HTML_PATTERNS:
        match = pattern.search(html)
        if match and (earliest is None or match.start() < earliest.start()):
            earliest = match
    if earliest is None:
        return html, None
    main = html[: earliest.start()].strip()
    quoted = html[earliest.start() :].strip()
    if not main:
        return html, None
    return _sanitize_html(main), _sanitize_html(quoted) if quoted else None


def _get_part_content(part: Message) -> str | None:
    try:
        content = part.get_content()
    except Exception:
        try:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        except Exception:
            return None
        return None
    if content is None:
        return None
    if isinstance(content, bytes):
        charset = part.get_content_charset() or "utf-8"
        return content.decode(charset, errors="replace")
    return str(content)


def _extract_bodies(msg: Message) -> tuple[str | None, str | None]:
    html_body: str | None = None
    plain_body: str | None = None

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue
            if part.get_content_disposition() == "attachment":
                continue
            ctype = part.get_content_type()
            if ctype == "text/html" and html_body is None:
                html_body = _get_part_content(part)
            elif ctype == "text/plain" and plain_body is None:
                plain_body = _get_part_content(part)
            elif ctype == "message/rfc822" and plain_body is None and html_body is None:
                nested = _unwrap_message(part)
                nested_html, nested_plain = _extract_bodies(nested)
                html_body = html_body or nested_html
                plain_body = plain_body or nested_plain
    else:
        ctype = msg.get_content_type()
        content = _get_part_content(msg)
        if ctype == "text/html":
            html_body = content
        else:
            plain_body = content

    return html_body, plain_body


def _extract_attachments(msg: Message) -> list[EmailAttachmentInfo]:
    adjuntos: list[EmailAttachmentInfo] = []
    for part in msg.walk():
        disposition = (part.get_content_disposition() or "").lower()
        if disposition != "attachment":
            continue
        filename = part.get_filename() or "adjunto"
        payload = part.get_payload(decode=True) or b""
        adjuntos.append(
            EmailAttachmentInfo(
                nombre=_decode_header(filename),
                content_type=part.get_content_type(),
                size=len(payload),
            )
        )
    return adjuntos


def parse_eml_for_view(content: bytes) -> EmailView:
    msg = BytesParser(policy=policy.default).parsebytes(content)
    msg = _unwrap_message(msg)

    asunto = _decode_header(msg.get("Subject")) or "(sin asunto)"
    remitente = _addresses(msg.get("From"))
    destinatario = _addresses(msg.get("To"))
    cc = _addresses(msg.get("Cc"))
    fecha = _format_fecha(msg)

    html_raw, plain_raw = _extract_bodies(msg)
    cuerpo_html = cita_html = cuerpo_texto = cita_texto = None

    if html_raw:
        cuerpo_html, cita_html = _split_html_reply(_sanitize_html(html_raw))
    if plain_raw:
        cuerpo_texto, cita_texto = _split_plain_reply(plain_raw)

    es_respuesta = bool(
        msg.get("In-Reply-To")
        or re.match(r"^\s*(re|aw|sv|antw|resp)\s*:", asunto, re.I)
        or cita_html
        or cita_texto
    )

    return EmailView(
        asunto=asunto,
        remitente=remitente,
        destinatario=destinatario,
        cc=cc,
        fecha=fecha,
        cuerpo_html=cuerpo_html,
        cuerpo_texto=cuerpo_texto,
        cita_html=cita_html,
        cita_texto=cita_texto,
        es_respuesta=es_respuesta,
        adjuntos=_extract_attachments(msg),
    )
