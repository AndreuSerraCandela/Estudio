"""Persona de medios del proyecto y aviso al comercial."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import settings
from app.services.bc_proyectos import BcProyectoError, _companies, _ident, _query, _text

BC_APP = "437dbf0e-84ff-417a-965d-ed2bb9650972"
BC_MALLA_EXT = "7a7d3479-e693-4f3d-8336-aac424523182"
USER_BC_EXT = "1e9ad503-229c-4aba-9116-e55e8281985a"
_ASIGNADO = f"Assigned User ID${BC_MALLA_EXT}"
_USER_BC = f"User BC${USER_BC_EXT}"


class MediosError(BcProyectoError):
    pass


@dataclass
class PersonaMedios:
    bc_user: str
    empleado: str
    nombre: str
    email: str

    def to_dict(self) -> dict:
        return {
            "bc_user": self.bc_user,
            "empleado": self.empleado,
            "nombre": self.nombre,
            "email": self.email,
        }


def mismo_empleado(izquierda: str | None, derecha: str | None) -> bool:
    a = (izquierda or "").strip()
    b = (derecha or "").strip()
    if not a or not b:
        return False
    if a == b:
        return True
    return a.lstrip("0") == b.lstrip("0") and bool(a.lstrip("0"))


def persona_del_proyecto(empresa: str | None, numero: str) -> PersonaMedios | None:
    numero = (numero or "").strip()
    if not numero:
        return None
    companies = _companies()
    if empresa and empresa.strip():
        companies = [item for item in companies if item.name.lower() == empresa.strip().lower()]
    for company in companies:
        persona = _persona_en_empresa(company, numero)
        if persona is not None:
            return persona
    return None


def persona_por_empleado(empleado: str) -> PersonaMedios | None:
    codigo = (empleado or "").strip()
    if not codigo:
        return None
    for persona in listar_personas():
        if mismo_empleado(persona.empleado, codigo):
            return persona
    return None


def listar_personas() -> list[PersonaMedios]:
    employee, extension = _tablas_empleado()
    rows = _query(
        f"SELECT e.[No_] AS empleado, "
        f"LTRIM(RTRIM(CONCAT(e.[First Name], ' ', e.[Last Name]))) AS nombre, "
        f"COALESCE(NULLIF(LTRIM(RTRIM(e.[Company E-Mail])), ''), LTRIM(RTRIM(e.[E-Mail]))) AS email, "
        f"u.[User Name] AS bc_user "
        f"FROM {employee} e "
        f"INNER JOIN {extension} x ON x.[No_] = e.[No_] "
        f"INNER JOIN [User] u ON u.[User Security ID] = x.[{_USER_BC}] "
        f"WHERE x.[{_USER_BC}] IS NOT NULL "
        f"AND x.[{_USER_BC}] <> '00000000-0000-0000-0000-000000000000' "
        f"AND COALESCE(NULLIF(LTRIM(RTRIM(e.[Company E-Mail])), ''), LTRIM(RTRIM(e.[E-Mail]))) <> '' "
        f"ORDER BY nombre"
    )
    personas: list[PersonaMedios] = []
    vistos: set[str] = set()
    for row in rows:
        persona = _persona_de_fila(row)
        if persona is None or persona.empleado in vistos:
            continue
        vistos.add(persona.empleado)
        personas.append(persona)
    return personas


def email_comercial(codigo: str | None, nombre: str | None = None) -> str:
    codigo = (codigo or "").strip()
    nombre = (nombre or "").strip()
    if not codigo and not nombre:
        return ""
    for company in _companies():
        tabla = _tabla(company, "Salesperson_Purchaser")
        if not tabla:
            continue
        if codigo:
            rows = _query(
                f"SELECT TOP 1 [E-Mail] AS email FROM {tabla} "
                f"WHERE LTRIM(RTRIM([Code])) = ?",
                [codigo],
            )
            email = _text(rows[0].get("email")) if rows else ""
            if email:
                return email
        if nombre:
            rows = _query(
                f"SELECT TOP 1 [E-Mail] AS email FROM {tabla} "
                f"WHERE LTRIM(RTRIM([Name])) = ?",
                [nombre],
            )
            email = _text(rows[0].get("email")) if rows else ""
            if email:
                return email
    return ""


def _persona_en_empresa(company, numero: str) -> PersonaMedios | None:
    if not company.job_ext:
        return None
    employee, extension = _tablas_empleado()
    rows = _query(
        f"SELECT TOP 1 e.[No_] AS empleado, "
        f"LTRIM(RTRIM(CONCAT(e.[First Name], ' ', e.[Last Name]))) AS nombre, "
        f"COALESCE(NULLIF(LTRIM(RTRIM(e.[Company E-Mail])), ''), LTRIM(RTRIM(e.[E-Mail]))) AS email, "
        f"u.[User Name] AS bc_user "
        f"FROM {_ident(company.job_ext)} j "
        f"INNER JOIN [User] u ON ("
        f"LTRIM(RTRIM(j.[{_ASIGNADO}])) = u.[User Name] "
        f"OR TRY_CONVERT(uniqueidentifier, j.[{_ASIGNADO}]) = u.[User Security ID]) "
        f"INNER JOIN {extension} x ON x.[{_USER_BC}] = u.[User Security ID] "
        f"INNER JOIN {employee} e ON e.[No_] = x.[No_] "
        f"WHERE j.[No_] = ? "
        f"AND LTRIM(RTRIM(ISNULL(j.[{_ASIGNADO}], ''))) <> '' "
        f"AND COALESCE(NULLIF(LTRIM(RTRIM(e.[Company E-Mail])), ''), LTRIM(RTRIM(e.[E-Mail]))) <> ''",
        [numero],
    )
    return _persona_de_fila(rows[0]) if rows else None


def _persona_de_fila(row: dict) -> PersonaMedios | None:
    empleado = _text(row.get("empleado"))
    email = _text(row.get("email"))
    if not empleado or not email:
        return None
    nombre = _text(row.get("nombre")) or empleado
    return PersonaMedios(
        bc_user=_text(row.get("bc_user")),
        empleado=empleado,
        nombre=nombre,
        email=email,
    )


def _tablas_empleado() -> tuple[str, str]:
    company = next((item for item in _companies() if item.name.lower() == settings.bc_company.lower()), None)
    if company is None:
        raise MediosError("No se encuentra la empresa de empleados de Business Central")
    employee = _tabla(company, "Employee")
    extension = f"{employee[1:-1]}$ext" if employee else ""
    if not employee or not _existe(extension):
        raise MediosError("No se encuentra la ficha de empleados de Business Central")
    return employee, _ident(extension)


def _tabla(company, nombre: str) -> str:
    physical = company.job.split("$Job$")[0]
    tabla = f"{physical}${nombre}${BC_APP}"
    if not _existe(tabla):
        return ""
    return _ident(tabla)


_existentes: set[str] | None = None


def _existe(tabla: str) -> bool:
    global _existentes
    if _existentes is None:
        _existentes = {str(row["TABLE_NAME"]) for row in _query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo'"
        )}
    return tabla in _existentes
