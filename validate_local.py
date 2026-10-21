"""Validación local del conector zendesk: ejercita las 5 capacidades.

Uso:
    python validate_local.py

Requiere RUVIC_ZENDESK_SUBDOMAIN, RUVIC_ZENDESK_EMAIL y RUVIC_ZENDESK_API_TOKEN
exportadas. ADVERTENCIA: crea un ticket REAL en la cuenta configurada (luego lo
marca como resuelto). Úsalo en una cuenta de pruebas.
"""

from ruvic_zendesk_connector import ZendeskClient, setup_logging

setup_logging("INFO")
client = ZendeskClient()

print("== 0. Ping ==")
client.ping()
print(f"  autenticado como {client.last_user}")

print("== 1. Crear ticket ==")
t = client.create_ticket("Prueba Ruvic QA", "Ticket creado por validate_local.py", priority="low", tags=["ruvic-qa"])
print(f"  ticket {t['id']} ({t['status']})")

print("== 2. Nota interna ==")
client.add_comment(t["id"], "Nota interna de validación", public=False)

print("== 3. Actualizar a solved ==")
print(f"  {client.update_ticket(t['id'], status='solved')['status']}")

print("== 4. Buscar ==")
for r in client.search_tickets("tags:ruvic-qa", limit=5):
    print(f"  {r['id']} {r['status']} {r['subject']}")

print("== 5. Consultar con comentarios ==")
print(f"  {len(client.get_ticket(t['id'], include_comments=True)['comments'])} comentario(s)")

print("\nTodo OK.")
