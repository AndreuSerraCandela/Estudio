from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user

from app.presencia.database import PresenciaSessionLocal
from app.presencia.models import UsuarioPresencia

bp = Blueprint("auth", __name__)


@bp.get("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("expedientes.list_expedientes"))

    return render_template("auth/login.html", error=None)


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
