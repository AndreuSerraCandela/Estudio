"""Utilidades para números de expediente."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.models import EstudioConfig, Expediente

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


def configuracion_estudio(db: Session) -> EstudioConfig:
    config = db.get(EstudioConfig, 1)
    if config is None:
        config = EstudioConfig(id=1, ot_automatica=False)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def ot_es_automatica(db: Session) -> bool:
    return bool(configuracion_estudio(db).ot_automatica)


def guardar_modo_ot(db: Session, automatica: bool) -> None:
    config = configuracion_estudio(db)
    config.ot_automatica = automatica
    db.commit()


def siguiente_numero_ot(db: Session) -> str:
    """Siguiente OT de la serie OT-000001, OT-000002…"""
    prefix = "OT-"
    width = 6
    max_num = 0
    for (ot,) in db.query(Expediente.ot).filter(Expediente.ot.isnot(None)).all():
        parsed = _parse_numero(ot or "")
        if parsed and parsed[0] == prefix:
            width = max(width, parsed[2])
            max_num = max(max_num, parsed[1])
    numero = max_num + 1
    while True:
        candidato = f"{prefix}{numero:0{width}d}"
        existe = db.query(Expediente.id).filter(Expediente.ot == candidato).first()
        if existe is None:
            return candidato
        numero += 1
