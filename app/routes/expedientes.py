import logging
from datetime import date, datetime, timezone
from pathlib import Path

from flask import Blueprint, abort, flash, g, jsonify, redirect, render_template, request, url_for, Response
from flask_login import current_user
from werkzeug.exceptions import HTTPException

from app.document_utils import documento_to_dict, guess_tipo, preview_kind
from app.expediente_utils import siguiente_numero_expediente
from app.models import Correo, Documento, Expediente, TipoDocumento
from app.services.bc import BCError, bc_service
from app.services.email_import import parse_eml_bytes, subject_marker
from app.services.email_view import parse_eml_for_view
from app.services.imap_sync import ImapError, buscar_correos_expediente_imap, guardar_copia_enviada_imap
from app.services.smtp_send import SmtpError, enviar_correo_smtp
from app.services.strapi import StrapiError, strapi_service
from app.services.user_config import (
    get_usuario_config,
    imap_configurado,
    imap_settings_from_config,
    smtp_settings_from_config,
)

bp = Blueprint("expedientes", __name__)
logger = logging.getLogger(__name__)


@bp.before_request
def require_login():
    if not current_user.is_authenticated:
        next_path = request.full_path if request.query_string else request.path
        if next_path.endswith("?") and not request.query_string:
            next_path = request.path
        return redirect(url_for("auth.login", next=next_path))


def _db():
    db = g.get("db")
    if db is None:
        abort(500, description="No hay conexión con la base de datos del estudio")
    return db


def _parse_date(value: str | None) -> date | None:
    if not value or not value.strip():
        return None
    return date.fromisoformat(value)


def _disenador_actual() -> str:
    return current_user.nombre_completo


def _expediente_from_form(form) -> dict:
    return {
        "numero_expediente": form.get("numero_expediente", "").strip(),
        "cliente": form.get("cliente", "").strip(),
        "bc_cliente_id": form.get("bc_cliente_id", "").strip() or None,
        "trabajo": form.get("trabajo", "").strip() or None,
        "comercial": form.get("comercial", "").strip() or None,
        "bc_comercial_id": form.get("bc_comercial_id", "").strip() or None,
        "ot": form.get("ot", "").strip() or None,
        "proyecto": form.get("proyecto", "").strip() or None,
        "bc_proyecto_id": form.get("bc_proyecto_id", "").strip() or None,
        "fecha_inicio": _parse_date(form.get("fecha_inicio")),
        "fecha_finalizacion": _parse_date(form.get("fecha_finalizacion")),
        "producto": form.get("producto", "").strip() or None,
        "acabado": form.get("acabado", "").strip() or None,
        "observaciones": form.get("observaciones", "").strip() or None,
        "disenador": _disenador_actual(),
    }


@bp.get("/api/vendedores")
def search_vendedores_api():
    q = request.args.get("q", "")
    try:
        vendedores = bc_service.search_vendedores(q)
        return jsonify([v.to_dict() for v in vendedores])
    except BCError as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("/api/proyectos")
def search_proyectos_api():
    q = request.args.get("q", "")
    try:
        proyectos = bc_service.search_proyectos(q)
        return jsonify([p.to_dict() for p in proyectos])
    except BCError as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("/api/clientes")
def search_clientes_api():
    q = request.args.get("q", "")
    try:
        clientes = bc_service.search_clientes(q)
        return jsonify([c.to_dict() for c in clientes])
    except BCError as exc:
        return jsonify({"error": str(exc)}), 502


@bp.get("")
def list_expedientes():
    db = _db()
    q = request.args.get("q", "")
    query = db.query(Expediente)
    if q.strip():
        term = f"%{q.strip()}%"
        query = query.filter(
            Expediente.numero_expediente.ilike(term)
            | Expediente.cliente.ilike(term)
            | Expediente.trabajo.ilike(term)
            | Expediente.proyecto.ilike(term)
        )
    expedientes = query.order_by(Expediente.created_at.desc()).all()
    return render_template("expedientes/list.html", expedientes=expedientes, q=q)


@bp.get("/nuevo")
def new_expediente_form():
    db = _db()
    return render_template(
        "expedientes/form.html",
        expediente=None,
        action=url_for("expedientes.create_expediente"),
        siguiente_numero=siguiente_numero_expediente(db),
    )


@bp.post("/nuevo")
def create_expediente():
    db = _db()
    data = _expediente_from_form(request.form)
    if not data["numero_expediente"] or not data["cliente"]:
        abort(400, description="Nº expediente y cliente son obligatorios")

    if db.query(Expediente).filter(Expediente.numero_expediente == data["numero_expediente"]).first():
        abort(400, description="Ya existe un expediente con ese número")

    expediente = Expediente(**data)
    db.add(expediente)
    db.commit()
    db.refresh(expediente)
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente.id))


@bp.get("/<int:expediente_id>")
def view_expediente(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    user_config = get_usuario_config(db, current_user.id)
    asunto_correo_default = f"{subject_marker(expediente.numero_expediente)} {expediente.cliente}"

    return render_template(
        "expedientes/detail.html",
        expediente=expediente,
        tipos_documento=[t.value for t in TipoDocumento],
        imap_configurado=imap_configurado(user_config),
        asunto_correo_default=asunto_correo_default,
        correos=sorted(
            expediente.correos,
            key=lambda c: c.fecha or c.created_at,
            reverse=True,
        ),
    )


@bp.get("/<int:expediente_id>/editar")
def edit_expediente_form(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    return render_template(
        "expedientes/form.html",
        expediente=expediente,
        action=url_for("expedientes.update_expediente", expediente_id=expediente_id),
    )


@bp.post("/<int:expediente_id>/editar")
def update_expediente(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    data = _expediente_from_form(request.form)
    existing = (
        db.query(Expediente)
        .filter(
            Expediente.numero_expediente == data["numero_expediente"],
            Expediente.id != expediente_id,
        )
        .first()
    )
    if existing:
        abort(400, description="Ya existe otro expediente con ese número")

    for key, value in data.items():
        setattr(expediente, key, value)

    expediente.disenador = _disenador_actual()
    expediente.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))


def _save_documento(
    db,
    expediente_id: int,
    content: bytes,
    filename: str,
    content_type: str | None,
    tipo: str | None = None,
    descripcion: str | None = None,
) -> Documento:
    if not content:
        abort(400, description="El archivo está vacío")

    if not tipo or tipo not in {t.value for t in TipoDocumento}:
        tipo = guess_tipo(filename, content_type)

    try:
        result = strapi_service.upload_file(content, filename, content_type)
    except StrapiError as exc:
        abort(502, description=str(exc))

    documento = Documento(
        expediente_id=expediente_id,
        strapi_id=result.strapi_id,
        strapi_document_id=result.strapi_document_id,
        url=result.url,
        nombre=result.nombre,
        tipo=tipo,
        descripcion=descripcion,
        mime_type=result.mime_type,
    )
    db.add(documento)
    db.commit()
    db.refresh(documento)
    return documento


@bp.post("/<int:expediente_id>/documentos")
def upload_documento(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        abort(400, description="Debe seleccionar un archivo")

    tipo = request.form.get("tipo", TipoDocumento.OTRO.value)
    descripcion = request.form.get("descripcion", "").strip() or None
    _save_documento(
        db,
        expediente_id,
        archivo.read(),
        archivo.filename,
        archivo.content_type,
        tipo=tipo,
        descripcion=descripcion,
    )
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))


@bp.post("/<int:expediente_id>/documentos/api")
def upload_documento_api(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        return jsonify({"error": "Expediente no encontrado"}), 404

    archivo = request.files.get("archivo")
    if not archivo or not archivo.filename:
        return jsonify({"error": "Debe seleccionar un archivo"}), 400

    tipo = request.form.get("tipo") or None
    descripcion = request.form.get("descripcion", "").strip() or None

    try:
        documento = _save_documento(
            db,
            expediente_id,
            archivo.read(),
            archivo.filename,
            archivo.content_type,
            tipo=tipo,
            descripcion=descripcion,
        )
    except HTTPException as exc:
        return jsonify({"error": exc.description}), exc.code

    return jsonify(documento_to_dict(documento))


@bp.post("/<int:expediente_id>/documentos/<int:documento_id>/eliminar")
def delete_documento(expediente_id: int, documento_id: int):
    db = _db()
    documento = (
        db.query(Documento)
        .filter(Documento.id == documento_id, Documento.expediente_id == expediente_id)
        .first()
    )
    if not documento:
        abort(404, description="Documento no encontrado")

    try:
        strapi_service.delete_file(documento.strapi_document_id, documento.strapi_id)
    except StrapiError:
        pass

    db.delete(documento)
    db.commit()
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))


@bp.get("/<int:expediente_id>/documentos/<int:documento_id>/vista")
def preview_documento(expediente_id: int, documento_id: int):
    db = _db()
    documento = (
        db.query(Documento)
        .filter(Documento.id == documento_id, Documento.expediente_id == expediente_id)
        .first()
    )
    if not documento:
        abort(404, description="Documento no encontrado")

    kind = preview_kind(documento)
    if kind == "other":
        abort(404, description="Vista previa no disponible para este tipo de archivo")

    import httpx

    try:
        response = httpx.get(documento.url, timeout=60, follow_redirects=True)
        response.raise_for_status()
    except Exception as exc:
        abort(502, description=f"No se pudo leer el documento: {exc}")

    if kind == "mail":
        try:
            mail_view = parse_eml_for_view(response.content)
        except Exception as exc:
            abort(502, description=f"No se pudo interpretar el correo: {exc}")
        return render_template("expedientes/documento_preview.html", mail=mail_view, documento=documento)

    content_type = response.headers.get("content-type") or documento.mime_type
    if kind == "pdf":
        content_type = "application/pdf"
    elif kind == "image" and not (content_type or "").startswith("image/"):
        content_type = documento.mime_type or "image/png"

    return Response(
        response.content,
        mimetype=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{documento.nombre}"',
            "X-Frame-Options": "SAMEORIGIN",
        },
    )


def _importar_correo(db, expediente_id: int, mail_info) -> Correo | None:
    if not mail_info.internet_message_id:
        return None

    existing = (
        db.query(Correo)
        .filter(Correo.internet_message_id == mail_info.internet_message_id)
        .first()
    )
    if existing:
        return None

    file_bytes = mail_info.file_bytes
    mime_type = mail_info.mime_type

    documento = _save_documento(
        db,
        expediente_id,
        file_bytes,
        mail_info.nombre_archivo,
        mime_type,
        tipo=TipoDocumento.MAIL.value,
        descripcion=f"{mail_info.direccion}: {mail_info.asunto}",
    )

    correo = Correo(
        expediente_id=expediente_id,
        direccion=mail_info.direccion,
        asunto=mail_info.asunto,
        destinatario=mail_info.destinatario,
        remitente=mail_info.remitente,
        fecha=mail_info.fecha,
        conversation_id=mail_info.conversation_id,
        outlook_entry_id=mail_info.outlook_entry_id,
        internet_message_id=mail_info.internet_message_id,
        documento_id=documento.id,
    )
    db.add(correo)
    db.commit()
    return correo


@bp.get("/<int:expediente_id>/correos/<int:correo_id>")
def ver_correo_expediente(expediente_id: int, correo_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    correo = (
        db.query(Correo)
        .filter(Correo.id == correo_id, Correo.expediente_id == expediente_id)
        .first()
    )
    if not correo or not correo.documento:
        abort(404, description="Correo no encontrado")

    import httpx

    try:
        response = httpx.get(correo.documento.url, timeout=60)
        response.raise_for_status()
        mail_view = parse_eml_for_view(response.content)
    except Exception as exc:
        abort(502, description=f"No se pudo leer el correo: {exc}")

    return render_template(
        "expedientes/correo_view.html",
        expediente=expediente,
        correo=correo,
        mail=mail_view,
    )


def _documentos_por_ids(db, expediente_id: int, raw_ids: list[str]) -> list[Documento]:
    ordered_ids: list[int] = []
    seen: set[int] = set()
    for raw_id in raw_ids:
        try:
            doc_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if doc_id in seen:
            continue
        ordered_ids.append(doc_id)
        seen.add(doc_id)

    if not ordered_ids:
        return []

    documentos = (
        db.query(Documento)
        .filter(Documento.expediente_id == expediente_id, Documento.id.in_(ordered_ids))
        .all()
    )
    by_id = {documento.id: documento for documento in documentos}
    return [by_id[doc_id] for doc_id in ordered_ids if doc_id in by_id]


def _cuerpo_con_enlaces(cuerpo: str, documentos: list[Documento]) -> str:
    if not documentos:
        return cuerpo

    enlaces = ["", "Documentos:"]
    enlaces.extend(f"- {documento.nombre}: {documento.url}" for documento in documentos)

    if cuerpo:
        return f"{cuerpo.rstrip()}\n\n{chr(10).join(enlaces).strip()}"
    return "\n".join(enlaces).strip()


@bp.post("/<int:expediente_id>/correos/enviar")
def enviar_correo_expediente(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    destinatario = request.form.get("destinatario", "").strip()
    asunto = request.form.get("asunto", "").strip()
    cuerpo = request.form.get("cuerpo", "").strip()
    documentos = _documentos_por_ids(db, expediente_id, request.form.getlist("documento_ids"))

    if not destinatario:
        flash("Indica un destinatario.", "error")
        return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))

    marker = subject_marker(expediente.numero_expediente)
    if marker not in asunto:
        asunto = f"{marker} {asunto}".strip() if asunto else f"{marker} {expediente.cliente}"

    config = get_usuario_config(db, current_user.id)
    settings = smtp_settings_from_config(config)
    if settings is None:
        flash("Configura correo en Configuración antes de enviar correos.", "error")
        return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))

    cuerpo_enviado = _cuerpo_con_enlaces(cuerpo, documentos)
    try:
        logger.info(
            "Enviando correo expediente %s con SMTP %s:%s usuario=%s ssl=%s tls=%s",
            expediente.numero_expediente,
            settings.host,
            settings.port,
            settings.username,
            settings.use_ssl,
            settings.use_tls,
        )
        eml_enviado = enviar_correo_smtp(settings, destinatario, asunto, cuerpo_enviado)
    except SmtpError as exc:
        logger.exception("Error SMTP al enviar expediente %s", expediente.numero_expediente)
        flash(str(exc), "error")
        return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))

    copia_imap_error = None
    if config.imap_guardar_copia_enviados:
        imap_settings = imap_settings_from_config(config)
        if imap_settings is None:
            copia_imap_error = "No se pudo obtener la configuración IMAP para guardar en Enviados."
        else:
            try:
                guardar_copia_enviada_imap(imap_settings, eml_enviado)
            except ImapError as exc:
                logger.exception("Correo enviado, pero no se pudo guardar copia IMAP en expediente %s", expediente.numero_expediente)
                copia_imap_error = str(exc)

    guardado_en_expediente = False
    try:
        mail_info = parse_eml_bytes(
            eml_enviado,
            f"enviado-{expediente.numero_expediente}.eml",
            direccion="enviado",
            usuario_email=current_user.email,
        )
        guardado_en_expediente = _importar_correo(db, expediente_id, mail_info) is not None
    except Exception:
        logger.exception("Correo enviado, pero no se pudo guardar en expediente %s", expediente.numero_expediente)

    if documentos:
        detalle = f" con {len(documentos)} enlace(s)"
    else:
        detalle = ""

    if guardado_en_expediente:
        mensaje = f"Correo enviado{detalle} y guardado en el expediente."
        if config.imap_guardar_copia_enviados:
            if copia_imap_error:
                mensaje += f" No se pudo guardar en IMAP Enviados: {copia_imap_error}"
                flash(mensaje, "warning")
            else:
                mensaje += " Copia guardada en IMAP Enviados."
                flash(mensaje, "success")
        else:
            flash(mensaje, "success")
    else:
        mensaje = f"Correo enviado{detalle}, pero no se pudo guardar la copia en el expediente. Revisa el log."
        if copia_imap_error:
            mensaje += f" Tampoco se pudo guardar en IMAP Enviados: {copia_imap_error}"
        flash(mensaje, "warning")
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))


@bp.post("/<int:expediente_id>/correos/sincronizar")
def sincronizar_correos_expediente(expediente_id: int):
    db = _db()
    expediente = db.get(Expediente, expediente_id)
    if not expediente:
        abort(404, description="Expediente no encontrado")

    config = get_usuario_config(db, current_user.id)
    settings = imap_settings_from_config(config)
    if settings is None:
        flash(
            "Configura IMAP en Configuración (servidor, usuario y contraseña) antes de sincronizar.",
            "error",
        )
        return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))

    try:
        logger.info(
            "Sincronizando correos expediente %s con IMAP %s:%s usuario=%s carpetas=%s/%s",
            expediente.numero_expediente,
            settings.host,
            settings.port,
            settings.username,
            settings.carpeta_entrada,
            settings.carpeta_enviados,
        )
        mails = buscar_correos_expediente_imap(
            settings,
            expediente.numero_expediente,
            usuario_email=current_user.email,
        )
    except ImapError as exc:
        logger.exception("Error IMAP al sincronizar expediente %s", expediente.numero_expediente)
        flash(str(exc), "error")
        return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))

    importados = 0
    for mail_info in mails:
        if _importar_correo(db, expediente_id, mail_info):
            importados += 1

    if importados:
        flash(f"Se importaron {importados} correo(s) desde IMAP.", "success")
    elif mails:
        flash(
            f"Se encontraron {len(mails)} correo(s) en IMAP, pero ya estaban importados en el estudio.",
            "info",
        )
    else:
        flash(
            "No hay correos nuevos. Busca mensajes cuyo asunto contenga "
            f"[EXP-{expediente.numero_expediente}] y vuelve a sincronizar. "
            f"Cuenta: {settings.username}. Carpetas: {settings.carpeta_entrada} / {settings.carpeta_enviados}.",
            "info",
        )
    return redirect(url_for("expedientes.view_expediente", expediente_id=expediente_id))
