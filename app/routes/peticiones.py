from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from flask_login import current_user
from sqlalchemy.orm import selectinload

from app.models import Peticion

bp = Blueprint("peticiones", __name__)


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
