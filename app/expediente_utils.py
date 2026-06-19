"""Utilidades para números de expediente."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Expediente

_NUMERO_SUFFIX = re.compile(r"^(.*?)(\d+)$")


def _parse_numero(numero: str) -> tuple[str, int, int] | None:
    match = _NUMERO_SUFFIX.match(numero.strip())
    if not match:
        return None
    prefix, digits = match.group(1), match.group(2)
    return prefix, int(digits), len(digits)


def siguiente_numero_expediente(db: Session) -> str:
    """Propone el siguiente número según el último expediente y el máximo del mismo prefijo."""
    ultimo = (
        db.query(Expediente)
        .order_by(Expediente.created_at.desc(), Expediente.id.desc())
        .first()
    )
    if ultimo is None:
        return f"{datetime.now().year}-001"

    parsed = _parse_numero(ultimo.numero_expediente)
    if parsed is None:
        return ultimo.numero_expediente

    prefix, _, width = parsed
    max_num = 0
    for (numero,) in db.query(Expediente.numero_expediente).all():
        item = _parse_numero(numero)
        if item and item[0] == prefix:
            max_num = max(max_num, item[1])

    return f"{prefix}{max_num + 1:0{width}d}"
