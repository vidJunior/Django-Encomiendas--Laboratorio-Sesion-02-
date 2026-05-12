# api/auth.py
# JWT personalizado con datos del empleado

from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
)

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
)

from api.throttles import LoginRateThrottle


# ── Serializer personalizado JWT ─────────────────────────────────

class EncomiendaTokenSerializer(TokenObtainPairSerializer):

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)

        # ── Datos básicos del usuario ────────────────────────────

        token['username'] = user.username

        token['email'] = user.email

        # ── Datos adicionales del empleado ───────────────────────

        try:

            emp = user.empleado

            token['empleado_id'] = emp.id

            token['empleado_cod'] = emp.codigo

            token['cargo'] = emp.cargo

        except Exception:
            pass

        return token


# ── View personalizada JWT ───────────────────────────────────────

class EncomiendaTokenView(TokenObtainPairView):

    throttle_classes = [LoginRateThrottle]

    serializer_class = EncomiendaTokenSerializer
