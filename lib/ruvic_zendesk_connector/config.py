"""Configuración del conector leída desde variables de entorno.

Convención de la plataforma: cada campo del formulario de configuración
llega como variable de entorno {ENV_PREFIX}{CAMPO} en mayúsculas.
Para este conector el prefijo es RUVIC_ZENDESK_.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

ENV_PREFIX = "RUVIC_ZENDESK_"


def _env_int(name: str, default: int) -> int:
    """Lee un entero tratando el string vacío como ausente: la plataforma
    envía "" cuando un campo opcional queda en blanco."""
    raw = (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(
            f"{ENV_PREFIX}{name} debe ser un número entero, no {raw!r}."
        ) from None
    if value <= 0:
        raise ValueError(f"{ENV_PREFIX}{name} debe ser mayor que 0, no {value}.")
    return value


def _env_bool(name: str, default: bool) -> bool:
    """Lee un booleano ("true"/"false"); vacío o ausente = default."""
    raw = (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip().lower()
    if not raw:
        return default
    if raw in ("true", "1", "yes", "si", "sí"):
        return True
    if raw in ("false", "0", "no"):
        return False
    raise ValueError(f"{ENV_PREFIX}{name} debe ser true o false, no {raw!r}.")


@dataclass(frozen=True)
class ZendeskConfig:
    """Parámetros de conexión a una cuenta de Zendesk Support (API Token)."""

    subdomain: str
    email: str
    api_token: str
    connect_timeout: int = 15

    @classmethod
    def from_env(cls) -> ZendeskConfig:
        """Construye la configuración desde las variables RUVIC_ZENDESK_*.

        Raises:
            ValueError: si falta alguna variable obligatoria o un valor no
                tiene el formato esperado.
        """
        missing = [
            f"{ENV_PREFIX}{name}"
            for name in ("SUBDOMAIN", "EMAIL", "API_TOKEN",)
            if not (os.environ.get(f"{ENV_PREFIX}{name}") or "").strip()
        ]
        if missing:
            raise ValueError(
                "Faltan variables de entorno del conector zendesk: "
                + ", ".join(missing)
                + ". Configura el conector en Settings → Conectores."
            )
        return cls(
            subdomain=os.environ[f"{ENV_PREFIX}SUBDOMAIN"].strip(),
            email=os.environ[f"{ENV_PREFIX}EMAIL"].strip(),
            api_token=os.environ[f"{ENV_PREFIX}API_TOKEN"],
            connect_timeout=_env_int("CONNECT_TIMEOUT", 15),
        )
