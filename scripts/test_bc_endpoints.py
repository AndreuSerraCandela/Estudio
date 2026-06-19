"""Explorar endpoints Vendedores y Proyectos en Business Central."""

from app.services.bc import bc_service

for entity, field in [("Vendedores", "Name"), ("Proyectos", "Description")]:
    print(f"\n=== {entity} search by {field} ===")
    try:
        rows = bc_service._get(entity, {"$filter": f"contains({field},'A')", "$top": "3"})
        for row in rows:
            key = row.get("Code") or row.get("No")
            label = row.get("Name") or row.get("Description")
            print(key, "-", label)
    except Exception as exc:
        print("error", exc)
