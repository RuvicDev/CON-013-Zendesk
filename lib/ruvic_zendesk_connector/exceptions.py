"""Excepciones propias del conector Zendesk.

Separan los tres tipos de fallo que el usuario debe distinguir:
autenticación, red/servidor y datos. Nunca exponemos excepciones
crípticas del cliente HTTP subyacente.
"""


class ZendeskConnectorError(Exception):
    """Error base del conector."""


class ZendeskAuthError(ZendeskConnectorError):
    """Credenciales inválidas o permisos insuficientes."""


class ZendeskNetworkError(ZendeskConnectorError):
    """No se pudo alcanzar el servicio (red, timeout o error del servidor)."""


class ZendeskDataError(ZendeskConnectorError):
    """La operación es válida pero los datos o parámetros no lo son."""
