"""Prueba de conexión estándar del conector zendesk.

Firma estándar Ruvic: def test_connection() -> tuple[bool, str]
- Lee la configuración EXCLUSIVAMENTE de las env vars RUVIC_ZENDESK_*.
- Nunca lanza excepciones; retorna (ok, mensaje).

Ejecutable también como script para pruebas locales:
    python test_connection.py
"""

from __future__ import annotations


def test_connection() -> tuple[bool, str]:
    """Consulta el usuario autenticado en Zendesk con las env vars RUVIC_ZENDESK_*."""
    try:
        from ruvic_zendesk_connector import (
            ZendeskAuthError,
            ZendeskClient,
            ZendeskDataError,
            ZendeskNetworkError,
        )
    except ImportError:
        return (
            False,
            (
                "La librería ruvic-zendesk-connector no está instalada. "
                "Instala con: pip install git+https://github.com/RuvicDev/"
                "CON-013-Zendesk.git#subdirectory=lib"
            ),
        )

    try:
        client = ZendeskClient()  # valida que existan las env vars
    except ValueError as exc:
        return False, str(exc)

    try:
        client.ping()
    except ZendeskAuthError as exc:
        return False, f"Autenticación fallida: {exc}"
    except ZendeskNetworkError as exc:
        return False, f"Error de red: {exc}"
    except ZendeskDataError as exc:
        return False, f"Error de datos: {exc}"
    except Exception as exc:  # noqa: BLE001 - red de seguridad: jamás propagar
        return False, f"Error inesperado: {exc}"

    return True, f"Conexión exitosa a Zendesk ({client.base_url}) como {client.last_user}"


if __name__ == "__main__":
    ok, message = test_connection()
    print(f"{'OK' if ok else 'FALLO'}: {message}")
    raise SystemExit(0 if ok else 1)
