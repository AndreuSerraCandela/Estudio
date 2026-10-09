"""Proyectos de Business Central leídos en SQL, igual que la web de peticiones."""

from __future__ import annotations

import threading
import time
from datetime import date, datetime

import pyodbc

from app.config import settings

BC_APP = "437dbf0e-84ff-417a-965d-ed2bb9650972"
BC_MALLA_EXT = "7a7d3479-e693-4f3d-8336-aac424523182"
_ESTADO_CONTRATO = {
    0: "Pendiente de Firma",
    1: "Firmado",
    2: "Anulado",
    3: "Cancelado",
    4: "Sin Montar",
    6: "Modificado",
}
_TIPO_LINEA = {0: "Recurso", 1: "Producto", 2: "Cuenta", 3: "Texto"}
_INVALID_COMPANY_CHARS = '."/\\\'%'
_CACHE_SECONDS = 600
_lock = threading.Lock()
_cache: dict | None = None
_cache_at = 0.0


class BcProyectoError(Exception):
    pass


class _Company:
    def __init__(self, name: str, job: str, job_ext: str | None, job_line: str | None, sales_header_ext: str | None):
        self.name = name
        self.job = job
        self.job_ext = job_ext
        self.job_line = job_line
        self.sales_header_ext = sales_header_ext


def buscar_proyectos(query: str, limit: int = 30) -> list[dict]:
    term = query.strip()
    if len(term) < 2:
        return []
    companies = _companies()
    if not companies:
        return []
    return [_proyecto_dict(row) for row in _union(companies, term, limit)]


def ficha_proyecto(empresa: str, numero: str) -> dict | None:
    company = _company_by_name(empresa)
    numero = numero.strip()
    if company is None or not numero:
        return None
    ext_cols = ""
    ext_join = ""
    if company.job_ext:
        ext_cols = (
            f", x.{_ext('Proyecto original')} AS proyecto_original, "
            f"x.{_ext('Proyecto origen')} AS proyecto_origen, "
            f"x.{_ext('Renovado')} AS renovado, "
            f"x.{_ext('Nombre Comercial')} AS anunciante, "
            f"x.{_ext('Fija_Papel')} AS fija_papel, "
            f"x.{_ext('Proyecto Antiguo')} AS proyecto_antiguo, "
            f"x.{_ext('Empresa Origen')} AS empresa_origen"
        )
        ext_join = f" LEFT JOIN {_ident(company.job_ext)} x ON x.[No_] = j.[No_]"
    estado_cols = ""
    estado_join = ""
    if company.sales_header_ext:
        estado_cols = ", contrato.estado AS estado_contrato"
        estado_join = (
            f" OUTER APPLY (SELECT TOP 1 sh.{_ext('Estado')} AS estado "
            f"FROM {_ident(company.sales_header_ext)} sh "
            f"WHERE sh.[Document Type] = 1 AND sh.{_ext('Nº Proyecto')} = j.[No_]) contrato"
        )
    rows = _query(
        f"SELECT j.[No_] AS numero, j.[Description] AS descripcion, "
        f"j.[Sell-to Customer Name] AS nombre_cliente, j.[Bill-to Name] AS facturar_a, "
        f"j.[Creation Date] AS fecha_creacion, j.[Starting Date] AS fecha_inicio, "
        f"j.[Ending Date] AS fecha_final{ext_cols}{estado_cols} "
        f"FROM {_ident(company.job)} j{ext_join}{estado_join} "
        f"WHERE j.[No_] = ?",
        [numero],
    )
    if not rows or _text(rows[0].get("empresa_origen")):
        return None
    row = rows[0]
    lineas = []
    if company.job_line:
        for linea in _query(
            f"SELECT [Type] AS tipo, [No_] AS numero, [Description] AS descripcion, "
            f"[Planning Date] AS fecha FROM {_ident(company.job_line)} "
            f"WHERE [Job No_] = ? ORDER BY [Job Task No_], [Line No_]",
            [numero],
        ):
            lineas.append(
                {
                    "tipo": _TIPO_LINEA.get(int(linea.get("tipo") or 0), ""),
                    "numero": _text(linea.get("numero")),
                    "descripcion": _text(linea.get("descripcion")),
                    "fecha": _date_text(linea.get("fecha")),
                }
            )
    estado = row.get("estado_contrato")
    return {
        "empresa": company.name,
        "numero": _text(row.get("numero")),
        "descripcion": _text(row.get("descripcion")),
        "anunciante": _text(row.get("anunciante")),
        "nombre_cliente": _text(row.get("nombre_cliente")),
        "facturar_a": _text(row.get("facturar_a")),
        "proyecto_original": _text(row.get("proyecto_original")),
        "proyecto_origen": _text(row.get("proyecto_origen")),
        "proyecto_antiguo": _text(row.get("proyecto_antiguo")),
        "renovado": bool(row.get("renovado")),
        "fija_papel": _fija_papel(row.get("fija_papel")),
        "fecha_creacion": _date_text(row.get("fecha_creacion")),
        "fecha_inicio": _date_text(row.get("fecha_inicio")),
        "fecha_final": _date_text(row.get("fecha_final")),
        "estado_contrato": _ESTADO_CONTRATO.get(int(estado), "") if estado is not None else "",
        "lineas": lineas,
    }


def _proyecto_dict(row: dict) -> dict:
    return {
        "no": _text(row.get("numero")),
        "description": _text(row.get("descripcion")),
        "empresa": _text(row.get("empresa")),
        "anunciante": _text(row.get("anunciante")),
        "nombre_cliente": _text(row.get("nombre_cliente")) or _text(row.get("cliente")),
        "fecha_inicio": _date_text(row.get("fecha_inicio")),
    }


def _union(companies: list[_Company], term: str, limit: int) -> list[dict]:
    parts: list[str] = []
    params: list = []
    since = _meses_atras(settings.bc_proyectos_meses)
    like = _like(term)
    for company in companies:
        sql, part_params = _proyecto_select(company, like, since)
        parts.append(sql)
        params.extend(part_params)
    statement = (
        f"SELECT TOP {int(limit)} * FROM ("
        + " UNION ALL ".join(parts)
        + ") AS busqueda ORDER BY fecha DESC"
    )
    return _query(statement, params)


def _proyecto_select(company: _Company, like: str, since: date) -> tuple[str, list]:
    join = ""
    ext_fields = "CAST('' AS nvarchar(255)) AS anunciante"
    interempresa = ""
    match = (
        "j.[No_] LIKE ? OR j.[Description] LIKE ? OR j.[Search Description] LIKE ? "
        "OR j.[Bill-to Name] LIKE ? OR j.[Sell-to Customer Name] LIKE ?"
    )
    match_params = [like, like, like, like, like]
    if company.job_ext:
        join = f" LEFT JOIN {_ident(company.job_ext)} e ON e.[No_] = j.[No_]"
        ext_fields = f"e.[Nombre Comercial${BC_MALLA_EXT}] AS anunciante"
        interempresa = f" AND LTRIM(RTRIM(ISNULL(e.[Empresa Origen${BC_MALLA_EXT}], ''))) = ''"
        match += f" OR e.[Nombre Comercial${BC_MALLA_EXT}] LIKE ?"
        match_params.append(like)
    sql = (
        f"SELECT ? AS empresa, j.[No_] AS numero, j.[Description] AS descripcion, "
        f"j.[Bill-to Name] AS cliente, j.[Sell-to Customer Name] AS nombre_cliente, "
        f"j.[Starting Date] AS fecha_inicio, "
        f"COALESCE(j.[Last Date Modified], j.[Creation Date], j.[Starting Date]) AS fecha, "
        f"{ext_fields} "
        f"FROM {_ident(company.job)} j{join} "
        f"WHERE (j.[Creation Date] >= ? OR j.[Last Date Modified] >= ? OR j.[Starting Date] >= ?) "
        f"AND ({match}){interempresa}"
    )
    return sql, [company.name, since, since, since, *match_params]


def _companies() -> list[_Company]:
    global _cache, _cache_at
    now = time.monotonic()
    with _lock:
        if _cache is not None and now - _cache_at < _CACHE_SECONDS:
            return _cache["companies"]
        companies = _discover()
        _cache = {"companies": companies}
        _cache_at = now
        return companies


def _discover() -> list[_Company]:
    existing = {str(row["TABLE_NAME"]) for row in _query(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'dbo'"
    )}
    found: list[_Company] = []
    for row in _query("SELECT [Name] AS name FROM [Company] ORDER BY [Name]"):
        name = _text(row.get("name"))
        if not name:
            continue
        physical = "".join("_" if char in _INVALID_COMPANY_CHARS else char for char in name)
        job = f"{physical}$Job${BC_APP}"
        if job not in existing:
            continue
        job_ext = f"{job}$ext"
        job_line = f"{physical}$Job Planning Line${BC_APP}"
        sales_header_ext = f"{physical}$Sales Header${BC_APP}$ext"
        found.append(
            _Company(
                name=name,
                job=job,
                job_ext=job_ext if job_ext in existing else None,
                job_line=job_line if job_line in existing else None,
                sales_header_ext=sales_header_ext if sales_header_ext in existing else None,
            )
        )
    return found


def _company_by_name(empresa: str) -> _Company | None:
    target = empresa.strip().lower()
    for company in _companies():
        if company.name.lower() == target:
            return company
    return None


def _query(statement: str, params: list | None = None) -> list[dict]:
    parts = [
        f"DRIVER={{{settings.db_driver}}}",
        f"SERVER={settings.bc_sql_server}",
        f"DATABASE={settings.bc_sql_database}",
        "TrustServerCertificate=yes",
    ]
    if settings.db_trusted_connection and settings.bc_sql_server == settings.db_server:
        parts.append("Trusted_Connection=yes")
    else:
        parts.extend([f"UID={settings.db_user}", f"PWD={settings.db_password}"])
    try:
        connection = pyodbc.connect(";".join(parts), timeout=20)
    except pyodbc.Error as exc:
        raise BcProyectoError("No se pudo conectar con la base de Business Central") from exc
    try:
        cursor = connection.cursor()
        cursor.execute(statement, params or [])
        columns = [column[0] for column in cursor.description or ()]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except pyodbc.Error as exc:
        raise BcProyectoError("La consulta de proyectos no se pudo completar") from exc
    finally:
        connection.close()


def _ext(field: str) -> str:
    return _ident(f"{field}${BC_MALLA_EXT}")


def _ident(name: str) -> str:
    if any(char in name for char in (";", "\n", "\r", "\x00")):
        raise BcProyectoError("Nombre de tabla no válido")
    return "[" + name.replace("]", "]]") + "]"


def _like(term: str) -> str:
    escaped = term.replace("[", "[[]").replace("%", "[%]").replace("_", "[_]")
    return f"%{escaped}%"


def _text(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _date_text(value) -> str | None:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return None


def _fija_papel(value) -> str:
    try:
        return {1: "Fija", 2: "Papel"}.get(int(value), "")
    except (TypeError, ValueError):
        return ""


def _meses_atras(meses: int) -> date:
    hoy = date.today()
    month = hoy.month - meses
    year = hoy.year
    while month <= 0:
        month += 12
        year -= 1
    if month == 2:
        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        last = 29 if leap else 28
    else:
        last = 30 if month in {4, 6, 9, 11} else 31
    return date(year, month, min(hoy.day, last))
