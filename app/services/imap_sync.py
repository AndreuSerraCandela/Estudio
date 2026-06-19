"""Sincronización de correos vía IMAP (Outlook Mac, Microsoft 365, etc.)."""

from __future__ import annotations

import imaplib
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from email import policy
from email.parser import BytesParser

from app.services.email_import import ImportedMailInfo, parse_eml_bytes
from app.services.email_import import subject_marker


class ImapError(Exception):
    pass


@dataclass
class ImapSettings:
    host: str
    port: int
    use_ssl: bool
    username: str
    password: str
    carpeta_entrada: str
    carpeta_enviados: str


def _quote_imap(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _connect(settings: ImapSettings) -> imaplib.IMAP4:
    try:
        if settings.use_ssl:
            client = imaplib.IMAP4_SSL(settings.host, settings.port)
        else:
            client = imaplib.IMAP4(settings.host, settings.port)
        client.login(settings.username, settings.password)
        return client
    except imaplib.IMAP4.error as exc:
        raise ImapError(f"Error de autenticación IMAP: {exc}") from exc
    except OSError as exc:
        raise ImapError(f"No se pudo conectar a {settings.host}:{settings.port}: {exc}") from exc


def _parse_folder_line(raw) -> str | None:
    if isinstance(raw, bytes):
        decoded = raw.decode("utf-8", errors="replace")
    else:
        decoded = str(raw)
    match = re.search(r'"((?:\\.|[^"\\])*)"\s*$', decoded)
    if match:
        return match.group(1).replace('\\"', '"').replace("\\\\", "\\")
    match = re.search(r'\)\s+"[^"]*"\s+(\S+)\s*$', decoded)
    if match:
        return match.group(1).strip('"')
    return None


def listar_carpetas_imap(settings: ImapSettings) -> list[str]:
    client = _connect(settings)
    try:
        status, folders = client.list()
        if status != "OK" or not folders:
            return []
        names: list[str] = []
        for entry in folders:
            if not entry:
                continue
            name = _parse_folder_line(entry)
            if name:
                names.append(name)
        return sorted(set(names))
    finally:
        try:
            client.logout()
        except Exception:
            pass


def probar_conexion_imap(settings: ImapSettings) -> list[str]:
    return listar_carpetas_imap(settings)


def _search_uids(client: imaplib.IMAP4, marker: str, since: datetime) -> list[bytes]:
    since_str = since.strftime("%d-%b-%Y")
    queries = [
        ("SUBJECT", _quote_imap(marker)),
        ("HEADER", "Subject", _quote_imap(marker)),
        ("TEXT", _quote_imap(marker)),
    ]
    uids: set[bytes] = set()
    for query in queries:
        try:
            status, data = client.search(None, "SINCE", since_str, *query)
        except imaplib.IMAP4.error:
            try:
                status, data = client.search(None, *query)
            except imaplib.IMAP4.error:
                continue
        if status != "OK" or not data or not data[0]:
            continue
        for uid in data[0].split():
            uids.add(uid)
    return sorted(uids, key=lambda value: int(value))


def _fetch_message(
    client: imaplib.IMAP4,
    uid: bytes,
    direccion: str,
    usuario_email: str | None,
) -> ImportedMailInfo | None:
    status, data = client.fetch(uid, "(RFC822)")
    if status != "OK" or not data or not data[0]:
        return None
    part = data[0]
    if not isinstance(part, tuple) or len(part) < 2:
        return None
    raw = part[1]
    if not isinstance(raw, (bytes, bytearray)):
        return None

    msg = BytesParser(policy=policy.default).parsebytes(raw)
    subject = str(msg.get("Subject") or "correo")
    safe_name = re.sub(r'[<>:"/\\|?*]', "_", subject)[:120] or "correo"
    return parse_eml_bytes(
        bytes(raw),
        f"{safe_name}.eml",
        direccion=direccion,
        usuario_email=usuario_email,
    )


def _select_folder(client: imaplib.IMAP4, carpeta: str) -> None:
    last_error: Exception | None = None
    for candidate in (carpeta, f'"{carpeta}"'):
        try:
            status, _ = client.select(candidate, readonly=True)
            if status == "OK":
                return
        except imaplib.IMAP4.error as exc:
            last_error = exc
    if last_error:
        raise ImapError(f"No se pudo abrir la carpeta «{carpeta}»: {last_error}") from last_error
    raise ImapError(f"No se pudo abrir la carpeta «{carpeta}»")


def _buscar_en_carpeta(
    client: imaplib.IMAP4,
    carpeta: str,
    direccion: str,
    marker: str,
    since: datetime,
    usuario_email: str | None,
) -> list[ImportedMailInfo]:
    _select_folder(client, carpeta.strip())

    resultados: list[ImportedMailInfo] = []
    for uid in _search_uids(client, marker, since):
        try:
            mail_info = _fetch_message(client, uid, direccion, usuario_email)
        except Exception:
            continue
        if mail_info:
            resultados.append(mail_info)
    return resultados


def buscar_correos_expediente_imap(
    settings: ImapSettings,
    numero_expediente: str,
    usuario_email: str | None = None,
    dias_atras: int = 180,
) -> list[ImportedMailInfo]:
    marker = subject_marker(numero_expediente)
    since = datetime.now() - timedelta(days=dias_atras)
    client = _connect(settings)

    try:
        carpetas = [
            (settings.carpeta_entrada, "recibido"),
            (settings.carpeta_enviados, "enviado"),
        ]
        resultados: list[ImportedMailInfo] = []
        vistos: set[str] = set()

        for carpeta, direccion in carpetas:
            if not carpeta.strip():
                continue
            for mail_info in _buscar_en_carpeta(client, carpeta.strip(), direccion, marker, since, usuario_email):
                if mail_info.internet_message_id in vistos:
                    continue
                vistos.add(mail_info.internet_message_id)
                resultados.append(mail_info)
        return resultados
    finally:
        try:
            client.logout()
        except Exception:
            pass
