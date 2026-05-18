# api/exceptions.py

import logging

from rest_framework import status

from rest_framework.response import Response

from rest_framework.views import (
    exception_handler,
)

from rest_framework.exceptions import (
    APIException,
)


logger = logging.getLogger(__name__)


def encomiendas_exception_handler(exc, context):
    """
    Handler global de errores para la API.

    Todas las respuestas mantienen
    el mismo formato:

    {
        "error": true,
        "code": "VALIDATION_ERROR",
        "message": "Descripción legible",
        "detail": { ... }
    }
    """

    # ── Procesar primero con DRF ─────────────────────────────────

    response = exception_handler(exc, context)

    # ── Errores controlados por DRF ──────────────────────────────

    if response is not None:
        error_code = "API_ERROR"

        message = "Ha ocurrido un error procesando la solicitud."

        # ── 400 Bad Request ──────────────────────────────────────

        if response.status_code == status.HTTP_400_BAD_REQUEST:
            error_code = "VALIDATION_ERROR"

            message = "Los datos enviados contienen errores de validación."

        # ── 401 Unauthorized ─────────────────────────────────────

        elif response.status_code == status.HTTP_401_UNAUTHORIZED:
            error_code = "AUTHENTICATION_REQUIRED"

            message = "Se requiere autenticación para acceder a este recurso."

        # ── 403 Forbidden ────────────────────────────────────────

        elif response.status_code == status.HTTP_403_FORBIDDEN:
            error_code = "PERMISSION_DENIED"

            message = "No tienes permiso para realizar esta acción."

        # ── 404 Not Found ────────────────────────────────────────

        elif response.status_code == status.HTTP_404_NOT_FOUND:
            error_code = "NOT_FOUND"

            message = "El recurso solicitado no existe."

        # ── 429 Too Many Requests ────────────────────────────────

        elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
            error_code = "RATE_LIMIT_EXCEEDED"

            message = "Se excedió el límite de solicitudes. Intenta más tarde."

        # ── Formato estándar de respuesta ────────────────────────

        original_data = response.data
        response.data = {
            "error": True,
            "code": error_code,
            "message": message,
            "detail": original_data,
        }
        if response.status_code == status.HTTP_400_BAD_REQUEST and isinstance(
            original_data, dict
        ):
            response.data.update(original_data)

        return response

    # ── Error no controlado (500) ────────────────────────────────

    logger.error(
        (f"Error no controlado en {context['view'].__class__.__name__}: {exc}"),
        exc_info=True,
    )

    return Response(
        {
            "error": True,
            "code": "INTERNAL_ERROR",
            "message": "Error interno del servidor.",
            "detail": None,
        },
        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ── Estado inválido ──────────────────────────────────────────────


class EstadoInvalidoError(APIException):
    """
    La transición de estado no es válida.
    """

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY

    default_code = "ESTADO_INVALIDO"

    default_detail = "La transición de estado no está permitida."


# ── Encomienda ya entregada ──────────────────────────────────────


class EncomiendaYaEntregadaError(APIException):
    """
    La encomienda ya fue entregada y
    no puede modificarse.
    """

    status_code = status.HTTP_409_CONFLICT

    default_code = "YA_ENTREGADA"

    default_detail = "La encomienda ya fue entregada y no puede modificarse."
