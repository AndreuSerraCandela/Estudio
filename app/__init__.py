import logging

from flask import Flask, g, jsonify, redirect, request, url_for

from app.auth_login import init_auth
from app.config import settings
from app.database import SessionLocal, init_db
from app.document_utils import documento_preview_attrs
from app.middleware import ForceHTTPSScheme
from app.routes.auth import bp as auth_bp
from app.routes.configuracion import bp as configuracion_bp
from app.routes.expedientes import bp as expedientes_bp

logger = logging.getLogger(__name__)

_PUBLIC_ENDPOINTS = {
    "health",
    "auth.login",
    "auth.login_post",
    "auth.logo_corporativo",
}


def _skip_db_for_request() -> bool:
    endpoint = request.endpoint or ""
    if endpoint in _PUBLIC_ENDPOINTS or endpoint.startswith("static"):
        return True
    return False
def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = settings.secret_key
    app.config["REMEMBER_COOKIE_DURATION"] = 60 * 60 * 24 * 14
    if settings.behind_https:
        app.config["SESSION_COOKIE_SECURE"] = True
        app.config["REMEMBER_COOKIE_SECURE"] = True
        app.config["PREFERRED_URL_SCHEME"] = "https"

    init_auth(app)

    if settings.behind_https:
        from werkzeug.middleware.proxy_fix import ProxyFix

        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1)
        app.wsgi_app = ForceHTTPSScheme(app.wsgi_app)

    if settings.init_db_on_startup:
        try:
            init_db()
        except Exception as exc:
            logger.exception("init_db falló al arrancar: %s", exc)
            app.config["INIT_DB_ERROR"] = str(exc)
    else:
        logger.info("ESTUDIO_INIT_DB=0: se omite init_db al arrancar")

    @app.get("/health")
    def health():
        err = app.config.get("INIT_DB_ERROR")
        payload = {"status": "ok" if not err else "degraded"}
        if err:
            payload["init_db_error"] = err
            return jsonify(payload), 503
        return jsonify(payload)

    @app.before_request
    def open_db():
        g.db = None
        if _skip_db_for_request():
            return
        g.db = SessionLocal()

    @app.before_request
    def log_request():
        if request.path not in ("/favicon.ico",):
            logger.info("%s %s", request.method, request.path)

    @app.teardown_appcontext
    def close_db(_exception=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    app.register_blueprint(auth_bp)
    app.register_blueprint(configuracion_bp, url_prefix="/configuracion")
    app.register_blueprint(expedientes_bp, url_prefix="/expedientes")

    @app.context_processor
    def inject_user():
        from flask_login import current_user

        return {"current_user": current_user, "documento_preview": documento_preview_attrs}

    return app
