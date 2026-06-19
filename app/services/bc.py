from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote

import requests

from app.config import settings


class BCError(Exception):
    pass


@dataclass
class BCCliente:
    no: str
    name: str
    search_name: str | None = None
    vat: str | None = None
    salesperson_code: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> BCCliente:
        return cls(
            no=str(row.get("No", "")).strip(),
            name=str(row.get("Name", "")).strip(),
            search_name=(row.get("Search_Name") or None),
            vat=(row.get("VAT_Registration_No") or None),
            salesperson_code=(row.get("Salesperson_Code") or None),
        )

    def to_dict(self) -> dict:
        return {
            "no": self.no,
            "name": self.name,
            "search_name": self.search_name,
            "vat": self.vat,
            "salesperson_code": self.salesperson_code,
        }


@dataclass
class BCVendedor:
    code: str
    name: str

    @classmethod
    def from_row(cls, row: dict) -> BCVendedor:
        return cls(
            code=str(row.get("Code", "")).strip(),
            name=str(row.get("Name", "")).strip(),
        )

    def to_dict(self) -> dict:
        return {"code": self.code, "name": self.name}


@dataclass
class BCProyecto:
    no: str
    description: str
    search_description: str | None = None

    @classmethod
    def from_row(cls, row: dict) -> BCProyecto:
        return cls(
            no=str(row.get("No", "")).strip(),
            description=str(row.get("Description", "")).strip(),
            search_description=(row.get("Search_Description") or None),
        )

    def to_dict(self) -> dict:
        return {
            "no": self.no,
            "description": self.description,
            "search_description": self.search_description,
        }


class BusinessCentralService:
    def __init__(
        self,
        base_url: str | None = None,
        company: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: int | None = None,
    ):
        self.base_url = (base_url or settings.bc_base_url).rstrip("/")
        self.company = company or settings.bc_company
        self.username = username if username is not None else settings.bc_username
        self.password = password if password is not None else settings.bc_password
        self.timeout = timeout if timeout is not None else settings.bc_timeout

    def _auth_header(self) -> str:
        if not self.username or not self.password:
            raise BCError("Credenciales de Business Central no configuradas")
        token = base64.b64encode(f"{self.username}:{self.password}".encode()).decode()
        return f"Basic {token}"

    def _entity_url(self, entity: str) -> str:
        company_encoded = quote(self.company)
        return f"{self.base_url}/powerbi/ODataV4/Company('{company_encoded}')/{entity}"

    @staticmethod
    def _odata_escape(value: str) -> str:
        return value.replace("'", "''")

    def _get(self, entity: str, params: dict | None = None) -> list[dict]:
        response = requests.get(
            self._entity_url(entity),
            headers={
                "Authorization": self._auth_header(),
                "Accept": "application/json",
            },
            params=params or {},
            timeout=self.timeout,
        )
        if response.status_code != 200:
            raise BCError(f"Error BC ({response.status_code}): {response.text[:300]}")

        payload = response.json()
        rows = payload.get("value", [])
        if not isinstance(rows, list):
            raise BCError("Respuesta inesperada de Business Central")
        return rows

    def _search(
        self,
        entity: str,
        query: str,
        limit: int,
        filters: list[str],
        parse_row: Callable[[dict], object | None],
        get_key: Callable[[object], str],
    ) -> list:
        term = query.strip()
        if len(term) < 2:
            return []

        escaped = self._odata_escape(term)
        seen: set[str] = set()
        results: list = []

        for filt in filters:
            if len(results) >= limit:
                break
            rows = self._get(
                entity,
                {"$filter": filt.format(q=escaped), "$top": str(limit)},
            )
            for row in rows:
                item = parse_row(row)
                if item is None:
                    continue
                key = get_key(item)
                if key and key not in seen:
                    seen.add(key)
                    results.append(item)

        return results[:limit]

    def search_clientes(self, query: str, limit: int = 20) -> list[BCCliente]:
        return self._search(
            "Clientes",
            query,
            limit,
            [
                "contains(Name,'{q}')",
                "contains(Search_Name,'{q}')",
                "contains(No,'{q}')",
            ],
            lambda row: BCCliente.from_row(row) if row.get("Name") else None,
            lambda item: item.no,
        )

    def search_vendedores(self, query: str, limit: int = 20) -> list[BCVendedor]:
        return self._search(
            "Vendedores",
            query,
            limit,
            [
                "contains(Name,'{q}')",
                "contains(Code,'{q}')",
            ],
            lambda row: BCVendedor.from_row(row) if row.get("Name") or row.get("Code") else None,
            lambda item: item.code,
        )

    def search_proyectos(self, query: str, limit: int = 20) -> list[BCProyecto]:
        return self._search(
            "Proyectos",
            query,
            limit,
            [
                "contains(Description,'{q}')",
                "contains(Search_Description,'{q}')",
                "contains(No,'{q}')",
            ],
            lambda row: BCProyecto.from_row(row) if row.get("No") else None,
            lambda item: item.no,
        )

    def get_cliente(self, no: str) -> BCCliente | None:
        client_no = no.strip()
        if not client_no:
            return None

        escaped = self._odata_escape(client_no)
        rows = self._get(
            "Clientes",
            {"$filter": f"No eq '{escaped}'", "$top": "1"},
        )
        if not rows:
            return None
        return BCCliente.from_row(rows[0])


bc_service = BusinessCentralService()
