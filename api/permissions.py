# api/permissions.py

from rest_framework.permissions import BasePermission

from envios.models import Empleado


# ── Permiso: empleado activo ─────────────────────────────────────


class EsEmpleadoActivo(BasePermission):
    """
    Solo empleados activos del sistema
    pueden acceder a la API.
    """

    message = "Solo empleados activos tienen acceso a esta API."

    def has_permission(self, request, view):

        if not request.user.is_authenticated:
            return False

        return bool(
            Empleado.objects.filter(email=request.user.email, estado=1).exists()
        )


# ── Permiso: propietario o admin ─────────────────────────────────


class EsPropietarioOAdmin(BasePermission):
    """
    El usuario puede ver/editar solo sus
    propias encomiendas, salvo admins.
    """

    def has_object_permission(self, request, view, obj):

        # Admin tiene acceso total
        if request.user.is_staff:
            return True

        # Solo el creador de la encomienda
        return obj.empleado_registro.email == request.user.email
