# api/throttles.py

from rest_framework.throttling import (
    AnonRateThrottle,
    UserRateThrottle,
)


# ── Login ────────────────────────────────────────────────────────


class LoginRateThrottle(AnonRateThrottle):
    """
    Limitar intentos de login:
    5 por minuto.
    """

    scope = "login_attempt"


# ── Requests generales de empleados ─────────────────────────────


class EmpleadoRateThrottle(UserRateThrottle):
    """
    Empleados autenticados:
    100 requests por minuto.
    """

    scope = "empleado"


# ── Cambios de estado ────────────────────────────────────────────


class CambioEstadoThrottle(UserRateThrottle):
    """
    Limitar cambios de estado:
    30 por hora.
    """

    scope = "cambio_estado"
