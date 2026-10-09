from flask import Blueprint, flash, g, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.expediente_utils import guardar_modo_ot, ot_es_automatica, siguiente_numero_ot
from app.services.imap_sync import ImapError, ImapSettings, listar_carpetas_imap, probar_conexion_imap
from app.services.user_config import (
    IMAP_DEFAULTS,
    SMTP_DEFAULTS,
    get_usuario_config,
    imap_configurado,
    imap_settings_from_config,
    set_imap_config,
)

bp = Blueprint("configuracion", __name__)


def _db():
    db = g.get("db")
    if db is None:
        from flask import abort

        abort(500, description="No hay conexión con la base de datos del estudio")
    return db


def _imap_settings_from_request(db) -> tuple[ImapSettings | None, str | None]:
    config = get_usuario_config(db, current_user.id)
    password = request.form.get("imap_password", "").strip()

    if password:
        host = request.form.get("imap_host", IMAP_DEFAULTS["host"])
        port_raw = request.form.get("imap_port", str(IMAP_DEFAULTS["port"]))
        use_ssl = request.form.get("imap_use_ssl") == "on"
        username = request.form.get("imap_username", "")
        carpeta_entrada = request.form.get("imap_carpeta_entrada", IMAP_DEFAULTS["carpeta_entrada"])
        carpeta_enviados = request.form.get("imap_carpeta_enviados", IMAP_DEFAULTS["carpeta_enviados"])
        try:
            port = int(port_raw)
        except ValueError:
            return None, "El puerto IMAP debe ser un número."
        return ImapSettings(
            host=host.strip() or IMAP_DEFAULTS["host"],
            port=port,
            use_ssl=use_ssl,
            username=username.strip(),
            password=password,
            carpeta_entrada=carpeta_entrada.strip() or IMAP_DEFAULTS["carpeta_entrada"],
            carpeta_enviados=carpeta_enviados.strip() or IMAP_DEFAULTS["carpeta_enviados"],
        ), None

    settings = imap_settings_from_config(config)
    if settings is None:
        return None, "Indica la contraseña IMAP o guarda la configuración antes de conectar."
    return settings, None


@bp.get("/")
@login_required
def ver_configuracion():
    db = _db()
    config = get_usuario_config(db, current_user.id)

    return render_template(
        "configuracion/form.html",
        config=config,
        imap_configurado=imap_configurado(config),
        imap_defaults=IMAP_DEFAULTS,
        smtp_defaults=SMTP_DEFAULTS,
        ot_automatica=ot_es_automatica(db),
        siguiente_ot=siguiente_numero_ot(db),
    )


@bp.post("/ot")
@login_required
def guardar_ot():
    db = _db()
    guardar_modo_ot(db, request.form.get("ot_modo") == "automatico")
    flash("Modo del número de OT guardado.", "success")
    return redirect(url_for("configuracion.ver_configuracion"))


@bp.post("/imap")
@login_required
def guardar_imap():
    db = _db()
    host = request.form.get("imap_host", IMAP_DEFAULTS["host"])
    port_raw = request.form.get("imap_port", str(IMAP_DEFAULTS["port"]))
    use_ssl = request.form.get("imap_use_ssl") == "on"
    username = request.form.get("imap_username", "")
    password = request.form.get("imap_password", "")
    carpeta_entrada = request.form.get("imap_carpeta_entrada", IMAP_DEFAULTS["carpeta_entrada"])
    carpeta_enviados = request.form.get("imap_carpeta_enviados", IMAP_DEFAULTS["carpeta_enviados"])
    guardar_copia_enviados = request.form.get("imap_guardar_copia_enviados") == "on"
    smtp_host = request.form.get("smtp_host", "")
    smtp_port_raw = request.form.get("smtp_port", str(SMTP_DEFAULTS["port"]))
    smtp_security = request.form.get("smtp_security", "tls")

    try:
        port = int(port_raw)
    except ValueError:
        flash("El puerto IMAP debe ser un número.", "error")
        return redirect(url_for("configuracion.ver_configuracion"))
    try:
        smtp_port = int(smtp_port_raw)
    except ValueError:
        flash("El puerto SMTP debe ser un número.", "error")
        return redirect(url_for("configuracion.ver_configuracion"))

    smtp_use_ssl = smtp_security == "ssl"
    smtp_use_tls = smtp_security == "tls"

    try:
        set_imap_config(
            db,
            current_user.id,
            host=host,
            port=port,
            use_ssl=use_ssl,
            username=username,
            password=password or None,
            carpeta_entrada=carpeta_entrada,
            carpeta_enviados=carpeta_enviados,
            guardar_copia_enviados=guardar_copia_enviados,
            smtp_host=smtp_host,
            smtp_port=smtp_port,
            smtp_use_tls=smtp_use_tls,
            smtp_use_ssl=smtp_use_ssl,
        )
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("configuracion.ver_configuracion"))

    flash("Configuración IMAP guardada.", "success")
    return redirect(url_for("configuracion.ver_configuracion"))


@bp.post("/imap/carpetas")
@login_required
def listar_carpetas_imap_api():
    db = _db()
    settings, error = _imap_settings_from_request(db)
    if error:
        return jsonify({"error": error}), 400
    if settings is None:
        return jsonify({"error": "No se pudo obtener la configuración IMAP."}), 400

    try:
        carpetas = listar_carpetas_imap(settings)
    except ImapError as exc:
        return jsonify({"error": str(exc)}), 502

    return jsonify({"carpetas": carpetas})


@bp.post("/imap/probar")
@login_required
def probar_imap():
    db = _db()
    settings, error = _imap_settings_from_request(db)
    if error:
        flash(error, "error")
        return redirect(url_for("configuracion.ver_configuracion"))
    if settings is None:
        flash("No se pudo obtener la configuración IMAP.", "error")
        return redirect(url_for("configuracion.ver_configuracion"))

    try:
        carpetas = probar_conexion_imap(settings)
    except ImapError as exc:
        flash(str(exc), "error")
        return redirect(url_for("configuracion.ver_configuracion"))

    muestra = ", ".join(carpetas[:12])
    if len(carpetas) > 12:
        muestra += f"… (+{len(carpetas) - 12} más)"
    flash(f"Conexión IMAP correcta. Carpetas detectadas: {muestra or '—'}", "success")
    return redirect(url_for("configuracion.ver_configuracion"))
