"""Punto de entrada para ejecutar la aplicación."""

from app import create_app
from app.config import settings

app = create_app()

if __name__ == "__main__":
    app.run(host=settings.host, port=settings.port, debug=settings.flask_debug)
