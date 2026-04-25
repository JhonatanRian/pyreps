from __future__ import annotations

from typing import Any
from ..contracts import DBConnection
from ..exceptions import InputAdapterError


def is_closed_connection_error(exc: Exception) -> bool:
    """Classify if an exception indicates a closed or invalid database connection."""
    error_type = type(exc).__name__.lower()
    if error_type in ("programmingerror", "interfaceerror", "operationalerror"):
        return True
    return "closed" in str(exc).lower()


def get_cursor(connection: DBConnection) -> Any:
    """
    Safely obtain a cursor from a connection, with unified error handling
    for closed or invalid connections.
    """
    # Proactive check for drivers that support the 'closed' attribute/method
    is_closed = getattr(connection, "closed", False)
    if callable(is_closed):
        is_closed = is_closed()

    if is_closed:
        raise InputAdapterError("The connection is closed.")

    try:
        return connection.cursor()
    except Exception as exc:
        if is_closed_connection_error(exc):
            raise InputAdapterError(
                f"Failed to create cursor. The connection might be closed or invalid. Original error: {exc}"
            ) from exc
        raise InputAdapterError(f"SQL cursor creation failed: {exc}") from exc
