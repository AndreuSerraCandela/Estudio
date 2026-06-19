from io import BytesIO

from flask import Blueprint, abort, flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.presencia.database import PresenciaSessionLocal
from app.presencia.models import UsuarioPresencia

bp = Blueprint("auth", __name__)


@bp.get("/")
@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("expedientes.list_expedientes"))

    return render_template("auth/login.html", error=None)


@bp.post("/")
@bp.post("/login")
def login_post():
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    remember = request.form.get("remember") == "on"

    db = PresenciaSessionLocal()
    try:
        user = db.query(UsuarioPresencia).filter(UsuarioPresencia.email == email).first()
        if user is None or not user.check_password(password):
            return render_template(
                "auth/login.html",
                error="Email o contraseña incorrectos",
                email=email,
            )
        if not user.is_active:
            return render_template(
                "auth/login.html",
                error="Usuario inactivo",
                email=email,
            )

        db.expunge(user)
        login_user(user, remember=remember)
    except SQLAlchemyError:
        return render_template(
            "auth/login.html",
            error=(
                "No se pudo conectar a la base de datos de usuarios "
                f"({settings.presencia_db_name}). Revisa PRESENCIA_DB_* en .env."
            ),
            email=email,
        )
    finally:
        db.close()

    next_page = request.args.get("next") or url_for("expedientes.list_expedientes")
    return redirect(next_page)


@bp.get("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


@bp.get("/usuario/foto")
@login_required
def foto_usuario_actual():
    db = PresenciaSessionLocal()
    try:
        user = db.get(UsuarioPresencia, current_user.id)
        if user is None or not user.foto_empleado_mimetype or not user.foto_empleado:
            abort(404)

        return send_file(
            BytesIO(bytes(user.foto_empleado)),
            mimetype=user.foto_empleado_mimetype,
            max_age=3600,
        )
    finally:
        db.close()


@bp.get("/corporativo/logo")
def logo_corporativo():
    logo_path = settings.corporativo_logo_path
    if not logo_path.is_file():
        abort(404)
    return send_file(logo_path, mimetype="image/png", max_age=86400)
