"""Prueba rápida del endpoint Clientes de Business Central."""

from app.services.bc import bc_service

if __name__ == "__main__":
    clientes = bc_service.search_clientes("EXPO")
    print(f"Encontrados: {len(clientes)}")
    for c in clientes[:5]:
        print(f"  {c.no} - {c.name}")
