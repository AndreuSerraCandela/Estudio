import os

from app.models import Documento, TipoDocumento


MAIL_EXTENSIONS = {".msg", ".eml", ".mbox"}
PDF_EXTENSIONS = {".pdf"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff"}
ARTE_EXTENSIONS = {".ai", ".eps", ".psd", ".indd", ".cdr"}


def guess_tipo(filename: str, content_type: str | None = None) -> str:
    ext = os.path.splitext(filename)[1].lower()
    name = filename.lower()

    if ext in MAIL_EXTENSIONS or (content_type or "").startswith("message/"):
        return TipoDocumento.MAIL.value
    if ext in PDF_EXTENSIONS or content_type == "application/pdf":
        return TipoDocumento.PDF.value
    if ext in IMAGE_EXTENSIONS or (content_type or "").startswith("image/"):
        return TipoDocumento.IMAGEN.value
    if ext in ARTE_EXTENSIONS or "arte" in name or "final" in name:
        return TipoDocumento.ARTE_FINAL.value
    return TipoDocumento.OTRO.value


def preview_kind(documento: Documento) -> str:
    mime = (documento.mime_type or "").lower()
    name = documento.nombre.lower()
    ext = os.path.splitext(name)[1]
    if documento.tipo == TipoDocumento.MAIL.value or mime.startswith("message/"):
        return "mail"
    if documento.tipo == TipoDocumento.PDF.value or mime == "application/pdf" or ext in PDF_EXTENSIONS:
        return "pdf"
    if documento.tipo == TipoDocumento.IMAGEN.value or mime.startswith("image/") or ext in IMAGE_EXTENSIONS:
        return "image"
    return "other"


def documento_preview_attrs(documento: Documento) -> dict[str, str]:
    kind = preview_kind(documento)
    if kind in ("mail", "pdf", "image"):
        src = f"/expedientes/{documento.expediente_id}/documentos/{documento.id}/vista"
    else:
        src = documento.url
    return {"kind": kind, "src": src}


def documento_to_dict(documento: Documento) -> dict:
    doc_id = documento.strapi_document_id or (str(documento.strapi_id) if documento.strapi_id else None)
    preview = documento_preview_attrs(documento)
    return {
        "id": documento.id,
        "nombre": documento.nombre,
        "url": documento.url,
        "tipo": documento.tipo,
        "tipo_label": documento.tipo.replace("_", " "),
        "descripcion": documento.descripcion,
        "document_id": doc_id,
        "preview_kind": preview["kind"],
        "preview_src": preview["src"],
        "delete_url": f"/expedientes/{documento.expediente_id}/documentos/{documento.id}/eliminar",
    }
