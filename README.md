# Conector Zendesk (CON-013)

Conector Ruvic de gestión de tickets para Zendesk Support (API v2): crear, actualizar, comentar, buscar y consultar tickets.

## Instalación

```bash
pip install git+https://github.com/RuvicDev/CON-013-Zendesk.git#subdirectory=lib
```

Python 3.10+. Dependencias: `requests>=2.31,<3.0`.

## Permisos requeridos

Autenticación con **correo del agente + API Token** (`{email}/token`).

1. En **Admin Center → Apps e integraciones → API de Zendesk → Configuración**, activa **Acceso por token**.
2. Pulsa **Agregar token de API**, dale un nombre (ej. "Ruvic") y copia el token: solo se muestra una vez.
3. El token actúa con los permisos del agente cuyo correo se configura. Usa un **agente dedicado** (rol Agente, no Administrador) con acceso solo a los grupos que el agente de IA deba gestionar.

## Variables de entorno (`RUVIC_ZENDESK_*`)

| Variable | Obligatoria | Descripción |
|----------|-------------|-------------|
| `RUVIC_ZENDESK_SUBDOMAIN` | Sí | Subdominio de Zendesk |
| `RUVIC_ZENDESK_EMAIL` | Sí | Correo del agente |
| `RUVIC_ZENDESK_API_TOKEN` | Sí | API Token |
| `RUVIC_ZENDESK_CONNECT_TIMEOUT` | No (default `15`) | Timeout de conexión (segundos) |

Los campos opcionales vacíos usan su valor por defecto (la plataforma envía
`""` cuando un campo queda en blanco).

## Pruebas locales

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ./lib

export RUVIC_ZENDESK_SUBDOMAIN=...
export RUVIC_ZENDESK_EMAIL=...
export RUVIC_ZENDESK_API_TOKEN=...

python test_connection.py
python validate_local.py
```

`validate_local.py` crea un ticket de prueba, lo comenta con una nota interna, lo marca como resuelto y lo busca. Úsalo en una cuenta de pruebas (Zendesk ofrece 14 días gratis).

## Notas de integración

- `search_tickets` y `get_ticket` son de solo lectura; `create_ticket`, `update_ticket` y `add_comment` escriben.
- Los comentarios son públicos por defecto (le llegan al solicitante por correo); `public=False` crea una nota interna.
- `update_ticket(tags=...)` reemplaza la lista completa de etiquetas.
- Si Zendesk responde 200 con un usuario anónimo, el conector lo trata como credenciales inválidas.
- Los errores 429 indican límite de peticiones del plan; el mensaje incluye cuántos segundos esperar.

## Limitaciones conocidas

- No elimina tickets ni gestiona usuarios, organizaciones o macros.
- No permite asignar el estado `closed` (Zendesk lo aplica solo a los tickets resueltos).
- `search_tickets` devuelve como máximo 100 resultados por llamada (sin paginación).
