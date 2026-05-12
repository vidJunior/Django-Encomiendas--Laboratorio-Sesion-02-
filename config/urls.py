# config/urls.py

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

# Vistas personalizadas web (conservadas para no romper UI del sistema)
from envios import views_auth

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

# Usamos el serializer personalizado que creamos antes para enriquecer el token
from api.auth import EncomiendaTokenView

urlpatterns = [
    # ── Admin Django ─────────────────────────────────────────────
    path("admin/", admin.site.urls),
    # ── Vistas web del sistema ──────────────────────────────────
    path("", include("envios.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    # Autenticación Web UI
    path("login/", views_auth.login_view, name="login"),
    path("logout/", views_auth.logout_view, name="logout"),
    path("perfil/", views_auth.perfil_view, name="perfil"),
    # ── API REST con versionado dinámico ────────────────────────
    # <version> captura: v1, v2, etc.
    path("api/<version>/", include("api.urls")),
    # ── JWT Auth ────────────────────────────────────────────────
    path("api/v1/auth/token/", EncomiendaTokenView.as_view(), name="token_obtain"),
    path(
        "api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"
    ),
    # ── Documentación OpenAPI ───────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger"
    ),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]


# ── Archivos estáticos y media en DEBUG ─────────────────────────
if settings.DEBUG:
    # ── Django Silk ──────────────────────────────────────────────
    # Profiling / performance dashboard
    urlpatterns += [
        path("silk/", include("silk.urls", namespace="silk")),
    ]

    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Personalización del Admin
admin.site.site_header = "Sistema de Gestión de Encomiendas"
admin.site.site_title = "Encomiendas Admin"
admin.site.index_title = "Panel de Administración"

# ── Ejemplos de uso ──────────────────────────────────────────────
# GET /api/v1/encomiendas/   -> versión 1
# GET /api/v2/encomiendas/   -> versión 2
