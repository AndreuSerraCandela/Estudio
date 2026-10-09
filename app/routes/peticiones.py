import base64
import mimetypes
from urllib.parse import urljoin

import requests
from flask import Blueprint, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Peticion, PeticionAdjunto

bp = Blueprint("peticiones", __name__)
DOCUMENT_VIEWER_DEFAULT_URL = "https://documentos.malla.es"


@bp.before_request
def require_login():
    if not current_user.is_authenticated:
        next_path = request.full_path if request.query_string else request.path
        if next_path.endswith("?") and not request.query_string:
            next_path = request.path
        return redirect(url_for("auth.login", next=next_path))
    return None


@bp.get("")
def listar():
    peticiones = (
        g.db.query(Peticion).options(selectinload(Peticion.adjuntos)).order_by(Peticion.created_at.desc()).all()
    )
    return render_template("peticiones/list.html", peticiones=peticiones)


def _viewer_url(path_or_url: str | None) -> str | None:
    if not path_or_url:
        return None
    path_or_url = str(path_or_url)
    if path_or_url.startswith(("http://", "https://")):
        return path_or_url
    return urljoin(f"{getattr(settings, 'document_viewer_url', DOCUMENT_VIEWER_DEFAULT_URL).rstrip('/')}/", path_or_url.lstrip("/"))


@bp.post("/adjuntos/<int:adjunto_id>/visor-session")
def crear_sesion_visor(adjunto_id: int):
    adjunto = g.db.get(PeticionAdjunto, adjunto_id)
    if not adjunto:
        return jsonify({"error": "Adjunto no encontrado"}), 404

    try:
        source_response = requests.get(adjunto.url, timeout=90, follow_redirects=True)
        source_response.raise_for_status()
    except requests.RequestException as exc:
        return jsonify({"error": f"No se pudo leer el adjunto: {exc}"}), 502

    content_type = (
        source_response.headers.get("content-type", "").split(";", 1)[0].strip()
        or adjunto.mime_type
        or mimetypes.guess_type(adjunto.nombre)[0]
        or "application/octet-stream"
    )
    payload = {
        "fileName": adjunto.nombre,
        "contentType": content_type,
        "contentBase64": base64.b64encode(source_response.content).decode("ascii"),
        "deleteAfter": True,
        "language": "es-ES",
    }

    try:
        viewer_response = requests.post(
            f"{getattr(settings, 'document_viewer_url', DOCUMENT_VIEWER_DEFAULT_URL).rstrip('/')}/api/session",
            json=payload,
            timeout=90,
        )
        viewer_response.raise_for_status()
        data = viewer_response.json()
    except requests.RequestException as exc:
        return jsonify({"error": f"No se pudo crear la sesión del visor: {exc}"}), 502
    except ValueError as exc:
        return jsonify({"error": f"Respuesta inesperada del visor: {exc}"}), 502

    if not isinstance(data, dict) or not data.get("embedUrl"):
        return jsonify({"error": "El visor no devolvió una sesión válida"}), 502

    return jsonify(
        {
            "nombre": adjunto.nombre,
            "originalUrl": adjunto.url,
            "previewId": data.get("previewId"),
            "kind": data.get("kind"),
            "embedUrl": _viewer_url(data.get("embedUrl")),
            "expandedUrl": _viewer_url(data.get("expandedUrl")),
        }
    )
