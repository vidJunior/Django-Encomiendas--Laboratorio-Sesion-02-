# envios/api_auth.py

from django.contrib.auth import authenticate

from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken


# ── Login con JWT en cookies HttpOnly ────────────────────────────


class LoginCookieView(APIView):
    # Permitir acceso sin autenticación
    permission_classes = []

    def post(self, request):

        username = request.data.get("username")

        password = request.data.get("password")

        user = authenticate(username=username, password=password)

        # ── Credenciales inválidas ───────────────────────────────

        if not user:
            return Response({"error": "Credenciales inválidas."}, status=401)

        # ── Generar tokens JWT ───────────────────────────────────

        refresh = RefreshToken.for_user(user)

        response = Response({"message": "Login exitoso."})

        # ── Access Token ─────────────────────────────────────────

        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,  # inaccesible desde JS
            secure=True,  # solo HTTPS
            samesite="Lax",  # protección CSRF
            max_age=3600,  # 1 hora
        )

        # ── Refresh Token ────────────────────────────────────────

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Lax",
            max_age=604800,  # 7 días
        )

        return response


# ── Logout eliminando cookies ────────────────────────────────────


class LogoutCookieView(APIView):
    def post(self, request):

        response = Response({"message": "Logout exitoso."})

        # Eliminar cookies JWT
        response.delete_cookie("access_token")

        response.delete_cookie("refresh_token")

        return response
