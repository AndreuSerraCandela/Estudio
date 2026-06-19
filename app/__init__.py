from flask import Flask, g, redirect, url_for

from app.auth_login import init_auth
from app.config import settings
from app.database import SessionLocal, init_db
from app.document_utils import documento_preview_attrs
from app.routes.auth import bp as auth_bp
from app.routes.configuracion import bp as configuracion_bp
from app.routes.expedientes import bp as expedientes_bp


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["REMEMBER_COOKIE_DURATION"] = 60 * 60 * 24 * 14

    init_auth(app)
    init_db()

    @app.before_request
    def open_db():
        g.db = SessionLocal()

    @app.teardown_appcontext
    def close_db(_exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    app.register_blueprint(auth_bp)
    app.register_blueprint(configuracion_bp, url_prefix="/configuracion")
    app.register_blueprint(expedientes_bp, url_prefix="/expedientes")

    @app.get("/")
    def root():
        return redirect(url_for("expedientes.list_expedientes"))

    @app.context_processor
    def inject_user():
        from flask_login import current_user

        return {"current_user": current_user, "documento_preview": documento_preview_attrs}

    return app
