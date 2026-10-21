"""Gestión de tickets de soporte en Zendesk: crear, actualizar, comentar y buscar tickets"""

from .client import ZendeskClient
from .config import ENV_PREFIX, ZendeskConfig
from .exceptions import (
    ZendeskAuthError,
    ZendeskConnectorError,
    ZendeskDataError,
    ZendeskNetworkError,
)
from .logging_utils import setup_logging

__all__ = [
    "ENV_PREFIX",
    "ZendeskAuthError",
    "ZendeskClient",
    "ZendeskConfig",
    "ZendeskConnectorError",
    "ZendeskDataError",
    "ZendeskNetworkError",
    "setup_logging",
]

__version__ = "1.0.0"
