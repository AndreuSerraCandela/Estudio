from datetime import date, datetime
from enum import Enum

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TipoDocumento(str, Enum):
    MAIL = "mail"
    PDF = "pdf"
    IMAGEN = "imagen"
    ARTE_FINAL = "arte_final"
    OTRO = "otro"


class Expediente(Base):
    __tablename__ = "expedientes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    numero_expediente: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    cliente: Mapped[str] = mapped_column(String(255), nullable=False)
    trabajo: Mapped[str | None] = mapped_column(Text)
    comercial: Mapped[str | None] = mapped_column(String(255))
    ot: Mapped[str | None] = mapped_column(String(100))
    proyecto: Mapped[str | None] = mapped_column(String(255))
    fecha_inicio: Mapped[date | None] = mapped_column(Date)
    fecha_finalizacion: Mapped[date | None] = mapped_column(Date)
    producto: Mapped[str | None] = mapped_column(String(255))
    acabado: Mapped[str | None] = mapped_column(String(255))
    observaciones: Mapped[str | None] = mapped_column(Text)
    disenador: Mapped[str | None] = mapped_column(String(255))

    # Campos reservados para integración futura con Business Central
    bc_cliente_id: Mapped[str | None] = mapped_column(String(100))
    bc_comercial_id: Mapped[str | None] = mapped_column(String(100))
    bc_proyecto_id: Mapped[str | None] = mapped_column(String(100))

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("SYSUTCDATETIME()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("SYSUTCDATETIME()"))

    documentos: Mapped[list["Documento"]] = relationship(
        "Documento", back_populates="expediente", cascade="all, delete-orphan"
    )
    correos: Mapped[list["Correo"]] = relationship(
        "Correo", back_populates="expediente", cascade="all, delete-orphan"
    )


class Correo(Base):
    __tablename__ = "correos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), nullable=False, index=True)
    direccion: Mapped[str] = mapped_column(String(20), nullable=False)
    asunto: Mapped[str | None] = mapped_column(String(500))
    destinatario: Mapped[str | None] = mapped_column(String(500))
    remitente: Mapped[str | None] = mapped_column(String(500))
    fecha: Mapped[datetime | None] = mapped_column(DateTime)
    conversation_id: Mapped[str | None] = mapped_column(String(255))
    outlook_entry_id: Mapped[str | None] = mapped_column(String(500))
    internet_message_id: Mapped[str | None] = mapped_column(String(500), index=True)
    documento_id: Mapped[int | None] = mapped_column(ForeignKey("documentos.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("SYSUTCDATETIME()"))

    expediente: Mapped["Expediente"] = relationship("Expediente", back_populates="correos")
    documento: Mapped["Documento | None"] = relationship("Documento")


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expediente_id: Mapped[int] = mapped_column(ForeignKey("expedientes.id"), nullable=False, index=True)
    strapi_id: Mapped[int] = mapped_column(Integer, nullable=False)
    strapi_document_id: Mapped[str | None] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(1024), nullable=False)
    nombre: Mapped[str] = mapped_column(String(512), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default=TipoDocumento.OTRO.value)
    descripcion: Mapped[str | None] = mapped_column(Text)
    mime_type: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("SYSUTCDATETIME()"))

    expediente: Mapped["Expediente"] = relationship("Expediente", back_populates="documentos")


class UsuarioConfig(Base):
    __tablename__ = "usuario_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    presencia_user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    imap_host: Mapped[str | None] = mapped_column(String(255))
    imap_port: Mapped[int] = mapped_column(Integer, default=993)
    imap_use_ssl: Mapped[bool] = mapped_column(Boolean, default=True)
    imap_username: Mapped[str | None] = mapped_column(String(255))
    imap_password_enc: Mapped[str | None] = mapped_column(Text)
    imap_carpeta_entrada: Mapped[str] = mapped_column(String(255), default="INBOX")
    imap_carpeta_enviados: Mapped[str] = mapped_column(String(255), default="Sent Items")
    imap_guardar_copia_enviados: Mapped[bool] = mapped_column(Boolean, default=False)
    smtp_host: Mapped[str | None] = mapped_column(String(255))
    smtp_port: Mapped[int | None] = mapped_column(Integer)
    smtp_use_tls: Mapped[bool] = mapped_column(Boolean, default=True)
    smtp_use_ssl: Mapped[bool] = mapped_column(Boolean, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=text("SYSUTCDATETIME()"))

