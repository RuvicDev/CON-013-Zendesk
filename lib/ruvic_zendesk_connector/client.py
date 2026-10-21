"""Cliente de gestión de tickets para Zendesk Support (API v2).

Capacidades:
- create_ticket():  crear un ticket.
- update_ticket():  actualizar estado, prioridad, asignación o etiquetas.
- add_comment():    agregar un comentario público o una nota interna.
- search_tickets(): buscar tickets con la sintaxis de búsqueda de Zendesk.
- get_ticket():     consultar un ticket por su ID.

Las credenciales SIEMPRE provienen de variables de entorno RUVIC_ZENDESK_*
(ver config.ZendeskConfig.from_env). Prohibido hardcodearlas.
"""

from __future__ import annotations

import re
from typing import Any

import requests

from .config import ZendeskConfig
from .exceptions import ZendeskAuthError, ZendeskDataError, ZendeskNetworkError
from .logging_utils import get_logger

_STATUSES = {"new", "open", "pending", "hold", "solved"}
_PRIORITIES = {"low", "normal", "high", "urgent"}
_SUBDOMAIN_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_TICKET_FIELDS = (
    "id", "subject", "status", "priority", "requester_id", "assignee_id",
    "group_id", "tags", "created_at", "updated_at",
)


def _require_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ZendeskDataError(f"{field} debe ser un texto no vacío.")
    return value.strip()


def _require_id(value: Any, field: str = "ticket_id") -> int:
    if isinstance(value, bool):
        raise ZendeskDataError(f"{field} debe ser un número entero positivo.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ZendeskDataError(f"{field} debe ser un número entero positivo, no {value!r}.") from None
    if number <= 0:
        raise ZendeskDataError(f"{field} debe ser un número entero positivo, no {value!r}.")
    return number


def _choice(value: str | None, allowed: set[str], field: str) -> str | None:
    if value is None:
        return None
    value = str(value).strip().lower()
    if value not in allowed:
        raise ZendeskDataError(f"{field} {value!r} inválido. Valores permitidos: {sorted(allowed)}")
    return value


def _summary(ticket: dict[str, Any]) -> dict[str, Any]:
    return {k: ticket.get(k) for k in _TICKET_FIELDS}


class ZendeskClient:
    """Cliente de tickets de Zendesk Support.

    Args:
        config: configuración de conexión. Si se omite, se lee de las
            variables de entorno RUVIC_ZENDESK_* (comportamiento estándar
            en el runtime de la plataforma).

    Ejemplo:
        >>> client = ZendeskClient()  # lee RUVIC_ZENDESK_* del entorno
        >>> client.get_ticket(123)
        {'id': 123, 'subject': 'No puedo ingresar', 'status': 'open', ...}
    """

    def __init__(self, config: ZendeskConfig | None = None) -> None:
        self.config = config or ZendeskConfig.from_env()
        subdomain = self.config.subdomain.lower().removesuffix(".zendesk.com")
        if not _SUBDOMAIN_RE.match(subdomain):
            raise ZendeskDataError(
                f"Subdominio inválido {self.config.subdomain!r}: usa solo la parte antes "
                "de .zendesk.com (ej. 'miempresa')."
            )
        self.base_url = f"https://{subdomain}.zendesk.com/api/v2"
        self.last_user: str | None = None
        self._logger = get_logger()
        self._session = requests.Session()
        self._session.auth = (f"{self.config.email}/token", self.config.api_token)
        self._session.headers.update({"Accept": "application/json"})

    # ------------------------------------------------------------------ #
    # Conexión
    # ------------------------------------------------------------------ #

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = self._session.request(
                method, f"{self.base_url}{path}", timeout=self.config.connect_timeout, **kwargs
            )
        except requests.exceptions.RequestException as exc:
            raise ZendeskNetworkError(f"No se pudo alcanzar Zendesk ({self.base_url}): {exc}") from exc

        if response.status_code == 401:
            raise ZendeskAuthError(
                "Correo o API Token inválidos, o el acceso por token está deshabilitado en "
                "Admin Center → Apps e integraciones → API de Zendesk."
            )
        if response.status_code == 403:
            raise ZendeskAuthError("El agente configurado no tiene permiso para esta operación.")
        if response.status_code == 404:
            raise ZendeskDataError("El ticket o recurso solicitado no existe.")
        if response.status_code == 422:
            raise ZendeskDataError(f"Zendesk rechazó los datos: {response.text[:300]}")
        if response.status_code == 429:
            retry = response.headers.get("Retry-After", "unos")
            raise ZendeskNetworkError(f"Límite de peticiones de Zendesk alcanzado; reintenta en {retry} segundos.")
        if response.status_code >= 500:
            raise ZendeskNetworkError(f"Zendesk respondió {response.status_code}; reintenta en unos segundos.")
        if response.status_code >= 400:
            raise ZendeskDataError(f"Zendesk respondió {response.status_code}: {response.text[:300]}")
        return response.json() if response.content else None

    def ping(self) -> bool:
        """Verifica las credenciales consultando el usuario autenticado.

        Returns:
            True si la conexión funciona.

        Raises:
            ZendeskAuthError / ZendeskNetworkError / ZendeskDataError.
        """
        try:
            user = (self._request("GET", "/users/me.json") or {}).get("user") or {}
        except ZendeskDataError as exc:
            raise ZendeskDataError(
                f"No existe una cuenta de Zendesk en {self.base_url.split('/api')[0]}: revisa el subdominio."
            ) from exc
        if not user.get("id"):
            # Zendesk responde 200 con un usuario anónimo si las credenciales no aplican
            raise ZendeskAuthError("Zendesk no reconoció las credenciales (usuario anónimo).")
        self.last_user = user.get("email")
        self._logger.info("Ping exitoso a Zendesk como %s", self.last_user)
        return True

    # ------------------------------------------------------------------ #
    # Capacidad 1: crear ticket
    # ------------------------------------------------------------------ #

    def create_ticket(
        self,
        subject: str,
        description: str,
        priority: str | None = None,
        requester_email: str | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Crea un ticket.

        Args:
            subject: asunto del ticket.
            description: descripción inicial (queda como primer comentario).
            priority: "low", "normal", "high" o "urgent" (opcional).
            requester_email: correo del solicitante; si se omite, el
                solicitante es el agente configurado.
            tags: etiquetas (opcional).

        Returns:
            Dict con id, subject, status, priority, requester_id, assignee_id,
            group_id, tags, created_at, updated_at.

        Ejemplo:
            >>> client.create_ticket("No puedo ingresar", "Error 403 al iniciar sesión", priority="high")
            {'id': 124, 'status': 'new', ...}
        """
        ticket: dict[str, Any] = {
            "subject": _require_text(subject, "subject"),
            "comment": {"body": _require_text(description, "description")},
        }
        if priority is not None:
            ticket["priority"] = _choice(priority, _PRIORITIES, "priority")
        if requester_email:
            ticket["requester"] = {"email": _require_text(requester_email, "requester_email")}
        if tags:
            ticket["tags"] = [str(t) for t in tags]
        result = self._request("POST", "/tickets.json", json={"ticket": ticket})["ticket"]
        self._logger.info("Ticket %s creado", result.get("id"))
        return _summary(result)

    # ------------------------------------------------------------------ #
    # Capacidad 2: actualizar ticket
    # ------------------------------------------------------------------ #

    def update_ticket(
        self,
        ticket_id: int,
        status: str | None = None,
        priority: str | None = None,
        assignee_id: int | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        """Actualiza estado, prioridad, agente asignado o etiquetas de un ticket.

        Args:
            ticket_id: ID del ticket.
            status: "new", "open", "pending", "hold" o "solved". ("closed"
                no se puede asignar: Zendesk cierra solo los tickets resueltos.)
            priority: "low", "normal", "high" o "urgent".
            assignee_id: ID numérico del agente a asignar.
            tags: lista que REEMPLAZA las etiquetas actuales.

        Ejemplo:
            >>> client.update_ticket(124, status="pending", priority="urgent")
            {'id': 124, 'status': 'pending', 'priority': 'urgent', ...}
        """
        ticket_id = _require_id(ticket_id)
        changes: dict[str, Any] = {}
        if status is not None:
            changes["status"] = _choice(status, _STATUSES, "status")
        if priority is not None:
            changes["priority"] = _choice(priority, _PRIORITIES, "priority")
        if assignee_id is not None:
            changes["assignee_id"] = _require_id(assignee_id, "assignee_id")
        if tags is not None:
            changes["tags"] = [str(t) for t in tags]
        if not changes:
            raise ZendeskDataError("Indica al menos un cambio: status, priority, assignee_id o tags.")
        result = self._request("PUT", f"/tickets/{ticket_id}.json", json={"ticket": changes})["ticket"]
        self._logger.info("Ticket %s actualizado: %s", ticket_id, sorted(changes))
        return _summary(result)

    # ------------------------------------------------------------------ #
    # Capacidad 3: comentar
    # ------------------------------------------------------------------ #

    def add_comment(self, ticket_id: int, body: str, public: bool = True) -> dict[str, Any]:
        """Agrega un comentario a un ticket.

        Args:
            ticket_id: ID del ticket.
            body: texto del comentario.
            public: True = visible para el solicitante; False = nota interna.

        Ejemplo:
            >>> client.add_comment(124, "Revisamos tu cuenta, ya puedes ingresar.")
            {'id': 124, 'status': 'open', ...}
        """
        ticket_id = _require_id(ticket_id)
        comment = {"body": _require_text(body, "body"), "public": bool(public)}
        result = self._request("PUT", f"/tickets/{ticket_id}.json", json={"ticket": {"comment": comment}})["ticket"]
        self._logger.info("Comentario %s agregado al ticket %s", "público" if public else "interno", ticket_id)
        return _summary(result)

    # ------------------------------------------------------------------ #
    # Capacidad 4: buscar tickets
    # ------------------------------------------------------------------ #

    def search_tickets(self, query: str = "", limit: int = 25) -> list[dict[str, Any]]:
        """Busca tickets con la sintaxis de búsqueda de Zendesk.

        Args:
            query: filtros de Zendesk, ej. "status:open priority:high",
                "requester:ana@cliente.com", "created>2026-10-01" o texto
                libre. Vacío = todos los tickets.
            limit: máximo de resultados (1-100, default 25).

        Returns:
            Lista de tickets (resumen), del más reciente al más antiguo.

        Ejemplo:
            >>> client.search_tickets("status:open priority:urgent", limit=10)
            [{'id': 124, 'subject': '...', 'status': 'open', ...}]
        """
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ZendeskDataError("limit debe ser un entero entre 1 y 100.")
        if not isinstance(query, str):
            raise ZendeskDataError("query debe ser un texto.")
        params = {
            "query": f"type:ticket {query.strip()}".strip(),
            "sort_by": "created_at",
            "sort_order": "desc",
            "per_page": limit,
        }
        results = (self._request("GET", "/search.json", params=params) or {}).get("results", [])
        self._logger.info("Búsqueda %r: %d ticket(s)", query, len(results))
        return [_summary(t) for t in results[:limit]]

    # ------------------------------------------------------------------ #
    # Capacidad 5: consultar un ticket
    # ------------------------------------------------------------------ #

    def get_ticket(self, ticket_id: int, include_comments: bool = False) -> dict[str, Any]:
        """Consulta un ticket por su ID.

        Args:
            ticket_id: ID del ticket.
            include_comments: si True, agrega la lista de comentarios
                (autor, texto, público/interno, fecha).

        Ejemplo:
            >>> client.get_ticket(124, include_comments=True)
            {'id': 124, ..., 'comments': [{'author_id': 1, 'body': '...', 'public': True, ...}]}
        """
        ticket_id = _require_id(ticket_id)
        result = _summary(self._request("GET", f"/tickets/{ticket_id}.json")["ticket"])
        if include_comments:
            comments = self._request("GET", f"/tickets/{ticket_id}/comments.json").get("comments", [])
            result["comments"] = [
                {k: c.get(k) for k in ("id", "author_id", "body", "public", "created_at")}
                for c in comments
            ]
        return result
