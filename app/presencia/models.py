from werkzeug.security import check_password_hash
from flask_login import UserMixin
from sqlalchemy import Boolean, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.presencia.database import PresenciaBase


class UsuarioPresencia(UserMixin, PresenciaBase):
    """Usuario de Control de Presencia (solo lectura para autenticación)."""

    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre: Mapped[str] = mapped_column(String(64), nullable=False)
    apellidos: Mapped[str] = mapped_column(String(128), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    foto_empleado: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    foto_empleado_mimetype: Mapped[str | None] = mapped_column(String(64), nullable=True)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellidos}".strip()

    @property
    def iniciales(self) -> str:
        return f"{(self.nombre or '')[:1]}{(self.apellidos or '')[:1]}".upper() or "U"

    @property
    def is_active(self) -> bool:
        return bool(self.activo)
