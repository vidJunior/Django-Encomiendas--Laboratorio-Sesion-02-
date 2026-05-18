from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # ── Consumer general: todos los empleados conectados ─────────
    # URL: ws://localhost:8000/ws/encomiendas/
    re_path(
        r'^ws/encomiendas/$',
        consumers.EncomiendaConsumer.as_asgi(),
        name='ws-encomiendas'
    ),
    # ── Consumer de detalle: una encomienda especifica ────────────
    # URL: ws://localhost:8000/ws/encomiendas/42/
    # El pk se extrae con el grupo con nombre (?P<pk>\d+)
    re_path(
        r'^ws/encomiendas/(?P<pk>\d+)/$',
        consumers.EncomiendaDetalleConsumer.as_asgi(),
        name='ws-encomienda-detalle'
    ),
    # ── Consumer del dashboard: estadisticas en tiempo real ───────
    # URL: ws://localhost:8000/ws/dashboard/
    re_path(
        r'^ws/dashboard/$',
        consumers.DashboardConsumer.as_asgi(),
        name='ws-dashboard'
    ),
]
