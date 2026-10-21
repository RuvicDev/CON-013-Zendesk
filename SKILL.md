---
name: zendesk
description: >
  Usa la librería ruvic_zendesk_connector para gestionar tickets de
  soporte en Zendesk - crear tickets (create_ticket), actualizar estado,
  prioridad o asignación (update_ticket), agregar comentarios públicos o
  notas internas (add_comment), buscar tickets (search_tickets) y consultar
  un ticket (get_ticket). Úsala cuando el usuario pida abrir, actualizar,
  comentar, buscar o revisar tickets o casos de soporte en Zendesk.
triggers:
- zendesk
- ticket
- tickets
- caso de soporte
- mesa de ayuda
- helpdesk
- soporte
---

# Conector Zendesk (ruvic_zendesk_connector)

Librería Python para gestionar tickets de Zendesk Support (API v2). Está **preinstalada en el runtime** cuando el
conector está configurado (si no, instálala con
`pip install git+https://github.com/RuvicDev/CON-013-Zendesk.git#subdirectory=lib`).

## Regla crítica de credenciales

El código generado **NUNCA hardcodea credenciales**. Siempre se leen de
variables de entorno, disponibles cuando el conector `zendesk` está
configurado:

| Variable | Contenido |
|----------|-----------|
| `RUVIC_ZENDESK_SUBDOMAIN` | Subdominio de Zendesk |
| `RUVIC_ZENDESK_EMAIL` | Correo del agente |
| `RUVIC_ZENDESK_API_TOKEN` | API Token |
| `RUVIC_ZENDESK_CONNECT_TIMEOUT` | (opcional) Timeout de conexión (segundos), default 15 |

Si estas variables NO existen, el conector no está configurado: no
generes código que lo use; indica al usuario que lo configure en
**Settings → Conectores**. El código generado **NUNCA** usa nombres con
segmento de alias (`_DEFAULT_INSTANCIA_`, `_PRODUCCION_`, etc.) salvo que
aparezcan en una sección autogenerada `## Variables en tu entorno` al final
de este skill.

## Este conector lee y escribe

`search_tickets` y `get_ticket` son de solo lectura. `create_ticket`,
`update_ticket` y `add_comment` **SÍ escriben** en la mesa de ayuda real:
un comentario público (`public=True`, el valor por defecto) le llega por
correo al cliente. Usa `public=False` para notas internas y confirma con el
usuario antes de enviar algo visible al cliente si no lo pidió explícitamente.

## Conexión (siempre igual)

```python
from ruvic_zendesk_connector import ZendeskClient

client = ZendeskClient()  # lee RUVIC_ZENDESK_* del entorno automáticamente
```

## Capacidad 1 — Crear un ticket

```python
ticket = client.create_ticket(
    "No puedo ingresar al portal",
    "El cliente reporta error 403 desde esta mañana",
    priority="high",                         # low | normal | high | urgent
    requester_email="ana@cliente.com",       # opcional
    tags=["portal", "acceso"],               # opcional
)
print(ticket["id"], ticket["status"])
```

## Capacidad 2 — Actualizar un ticket

```python
client.update_ticket(124, status="pending", priority="urgent")
client.update_ticket(124, assignee_id=3721, tags=["escalado"])  # tags REEMPLAZA las actuales
```

Estados permitidos: `new`, `open`, `pending`, `hold`, `solved`. `closed` no se
puede asignar: Zendesk cierra automáticamente los tickets resueltos.

## Capacidad 3 — Comentar un ticket

```python
client.add_comment(124, "Ya restablecimos tu acceso.")                 # público
client.add_comment(124, "Revisar logs del WAF", public=False)          # nota interna
```

## Capacidad 4 — Buscar tickets

```python
abiertos = client.search_tickets("status:open priority:urgent", limit=10)
del_cliente = client.search_tickets("requester:ana@cliente.com")
recientes = client.search_tickets("created>2026-10-01")
```

Usa la sintaxis de búsqueda de Zendesk; el conector agrega `type:ticket` solo.

## Capacidad 5 — Consultar un ticket

```python
detalle = client.get_ticket(124, include_comments=True)
for c in detalle["comments"]:
    print(c["created_at"], "público" if c["public"] else "interno", c["body"][:80])
```

## Manejo de errores

```python
from ruvic_zendesk_connector import (
    ZendeskAuthError, ZendeskDataError, ZendeskNetworkError,
)

try:
    client.update_ticket(124, status="solved")
except ZendeskAuthError as e:
    print(f"Credenciales o permisos: {e}")
except ZendeskNetworkError as e:
    print(f"No se pudo alcanzar el servicio: {e}")
except ZendeskDataError as e:
    print(f"Error de datos: {e}")
```

Muestra el mensaje de la excepción tal cual al usuario: indica qué corregir.

## Buenas prácticas al generar código

1. Lee credenciales SOLO de las variables `RUVIC_ZENDESK_*` (el constructor de `ZendeskClient` ya lo hace).
2. Nunca imprimas `RUVIC_ZENDESK_API_TOKEN` en logs ni en la salida.
3. Antes de actualizar o comentar, confirma con `get_ticket` que el ID corresponde al caso del que habla el usuario.
4. Los comentarios son públicos por defecto: usa `public=False` para notas internas.
5. Usa `limit` razonable en `search_tickets` (máximo 100).
