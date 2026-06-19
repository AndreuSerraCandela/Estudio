from __future__ import annotations

from typing import Callable


class ForceHTTPSScheme:
    """Fuerza wsgi.url_scheme=https cuando IIS termina TLS y no envía X-Forwarded-Proto."""

    def __init__(self, app: Callable):
        self.app = app

    def __call__(self, environ, start_response):
        environ["wsgi.url_scheme"] = "https"
        if not environ.get("HTTP_X_FORWARDED_PROTO"):
            environ["HTTP_X_FORWARDED_PROTO"] = "https"
        return self.app(environ, start_response)
