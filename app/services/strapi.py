from __future__ import annotations

import base64
import mimetypes
import os
from dataclasses import dataclass

import requests

from app.config import settings


@dataclass
class StrapiUploadResult:
    strapi_id: int
    strapi_document_id: str | None
    url: str
    nombre: str
    mime_type: str | None


class StrapiError(Exception):
    pass


class StrapiService:
    """Cliente del repositorio base64-api (mismo servicio que usa Incidencias)."""

    IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "tif", "tiff", "gif"}

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.strapi_url).rstrip("/")

    def _save_url(self) -> str:
        return f"{self.base_url}/save"

    def _delete_url(self) -> str:
        return f"{self.base_url}/delete"

    @staticmethod
    def _base64_payload(file_content: bytes, filename: str, content_type: str | None) -> str:
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        encoded = base64.b64encode(file_content).decode("ascii")

        if ext in StrapiService.IMAGE_EXTENSIONS:
            mime = content_type or f"image/{ext}"
            if ext == "jpg":
                mime = "image/jpeg"
            return f"{mime};base64,{encoded}"

        guessed = content_type or mimetypes.guess_type(filename)[0]
        mime = guessed or f"application/{ext or 'octet-stream'}"
        return f"{mime};base64,{encoded}"

    def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str | None = None,
    ) -> StrapiUploadResult:
        payload = {
            "base64": self._base64_payload(file_content, filename, content_type),
            "filename": filename,
        }

        response = requests.post(
            self._save_url(),
            json=payload,
            timeout=120,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code >= 400:
            raise StrapiError(
                f"Error al subir documento ({response.status_code}): {response.text[:300]}"
            )

        data = response.json()
        url = data.get("url", "")
        file_id = data.get("_id")
        file_id_str = str(file_id) if file_id is not None else ""
        strapi_id = int(file_id) if file_id_str.isdigit() else 0

        if not url or not file_id_str:
            raise StrapiError("Respuesta inesperada del repositorio de documentos")

        return StrapiUploadResult(
            strapi_id=strapi_id,
            strapi_document_id=file_id_str,
            url=url,
            nombre=filename,
            mime_type=content_type or mimetypes.guess_type(filename)[0],
        )

    def delete_file(self, document_id: str | None, strapi_id: int | None = None) -> None:
        file_id = (document_id or "").strip()
        if not file_id and strapi_id:
            file_id = str(strapi_id)
        if not file_id:
            return

        response = requests.delete(
            self._delete_url(),
            json={"_id": file_id},
            timeout=30,
            headers={"Content-Type": "application/json"},
        )

        if response.status_code in {200, 204, 404}:
            return

        raise StrapiError(
            f"Error al eliminar documento ({response.status_code}): {response.text[:300]}"
        )


strapi_service = StrapiService()
