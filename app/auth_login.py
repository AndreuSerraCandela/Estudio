from flask import Flask
from flask_login import LoginManager

from app.presencia.database import PresenciaSessionLocal
from app.presencia.models import UsuarioPresencia

login_manager = LoginManager()


def init_auth(app: Flask) -> None:
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Inicia sesión para acceder al estudio."
    login_manager.login_message_category = "warning"


@login_manager.user_loader
def load_user(user_id: str):
    db = PresenciaSessionLocal()
    try:
        user = db.get(UsuarioPresencia, int(user_id))
        if user is None or not user.is_active:
            return None
        db.expunge(user)
        return user
    finally:
        db.close()
