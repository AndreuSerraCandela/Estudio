"""Prueba de subida al repositorio base64-api."""

from app.services.strapi import strapi_service

if __name__ == "__main__":
    content = b"test estudio upload"
    result = strapi_service.upload_file(content, "test-estudio.txt", "text/plain")
    print("url:", result.url)
    print("id:", result.strapi_document_id)
    strapi_service.delete_file(result.strapi_document_id)
    print("delete ok")
