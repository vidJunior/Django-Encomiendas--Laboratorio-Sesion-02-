# envios/urls.py
from django.urls import path
from . import views
from . import views_cbv
from . import views_async

urlpatterns = [
    # ── Vistas Async (Nuevas) ──────────────────────────────────
    path(
        "api/dashboard/stats/",
        views_async.dashboard_stats_async,
        name="api_dashboard_stats",
    ),
    # ── Vistas de Funciones (Lógica personalizada) ────────────────
    path("", views.dashboard, name="dashboard"),
    path(
        "encomiendas/<int:pk>/estado/",
        views.encomienda_cambiar_estado,
        name="encomienda_cambiar_estado",
    ),
    path(
        "encomiendas/buscar/<str:codigo>/",
        views.buscar_por_codigo,
        name="buscar_por_codigo",
    ),
    # ── Vistas Basadas en Clases (CBV - CRUD estándar) ────────────
    path(
        "encomiendas/", views_cbv.EncomiendaListView.as_view(), name="encomienda_lista"
    ),
    path(
        "encomiendas/nueva/",
        views_cbv.EncomiendaCreateView.as_view(),
        name="encomienda_crear",
    ),
    path(
        "encomiendas/<int:pk>/",
        views_cbv.EncomiendaDetailView.as_view(),
        name="encomienda_detalle",
    ),
    path(
        "encomiendas/<int:pk>/editar/",
        views_cbv.EncomiendaUpdateView.as_view(),
        name="encomienda_editar",
    ),
    path("health/", views.health_check, name="health"),
]
