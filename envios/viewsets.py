# envios/viewsets.py

from django.db.models import Q
from django.core.cache import cache
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from config.settings import CACHE_TTL

from drf_spectacular.types import OpenApiTypes

from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from api.throttles import (
    CambioEstadoThrottle,
    EmpleadoRateThrottle,
)

from api.pagination import (
    EncomiendaPagination,
    HistorialPagination,
)

from .models import Encomienda, Empleado, Ruta

from .serializers import (
    EncomiendaSerializer,
    EncomiendaListSerializer,
    EncomiendaDetailSerializer,
    EncomiendaV2Serializer,
    HistorialEstadoSerializer,
    RutaSerializer,
)


# ────────────────────────────────────────────────────────────────
# RUTAS
# ────────────────────────────────────────────────────────────────


class RutaViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Las rutas cambian poco.
    Cachear listado por 15 minutos.
    """

    queryset = Ruta.objects.activas()
    serializer_class = RutaSerializer

    # ── Cache HTTP ───────────────────────────────────────────────
    @method_decorator(cache_page(CACHE_TTL))
    @method_decorator(vary_on_headers("Authorization"))
    def list(self, request, *args, **kwargs):
        """
        Cache por usuario/token.
        """
        return super().list(request, *args, **kwargs)


# ── Documentación automática para acciones estándar ──────────────


@extend_schema_view(
    list=extend_schema(
        summary="Listar encomiendas",
        description="""
        Devuelve la lista paginada de encomiendas.

        Soporta:
        - filtros por estado
        - búsqueda
        - ordenamiento
        """,
        tags=["Encomiendas"],
    ),
    create=extend_schema(
        summary="Crear encomienda",
        description="""
        Registra una nueva encomienda
        en el sistema.
        """,
        tags=["Encomiendas"],
    ),
    retrieve=extend_schema(
        summary="Detalle de encomienda",
        description="""
        Devuelve los datos completos de una encomienda:

        - remitente
        - destinatario
        - ruta
        - historial de estados
        """,
        tags=["Encomiendas"],
    ),
    update=extend_schema(
        summary="Actualizar encomienda",
        tags=["Encomiendas"],
    ),
    partial_update=extend_schema(
        summary="Actualizar parcialmente",
        tags=["Encomiendas"],
    ),
    destroy=extend_schema(
        summary="Eliminar encomienda",
        tags=["Encomiendas"],
    ),
)
class EncomiendaViewSet(viewsets.ModelViewSet):
    queryset = Encomienda.objects.con_relaciones()

    serializer_class = EncomiendaSerializer

    permission_classes = [IsAuthenticated]

    pagination_class = EncomiendaPagination

    # Throttle general del ViewSet
    throttle_classes = [EmpleadoRateThrottle]

    def get_throttles(self):
        """
        Throttle dinámico según acción.
        """

        # Acción sensible:
        # cambiar estado
        if self.action == "cambiar_estado":
            return [CambioEstadoThrottle()]

        return super().get_throttles()

    # ── Serializer dinámico según versión y acción ──────────────
    def get_serializer_class(self):
        """
        Elegir serializer según versión y acción.

        v1:
            list      -> EncomiendaListSerializer
            retrieve  -> EncomiendaDetailSerializer
            write     -> EncomiendaSerializer

        v2:
            cualquier acción -> EncomiendaV2Serializer
        """
        version = getattr(self.request, "version", "v1")

        # ── API v2 ───────────────────────────────────────────────
        if version == "v2":
            return EncomiendaV2Serializer

        # ── API v1 ───────────────────────────────────────────────
        if self.action == "list":
            return EncomiendaListSerializer
        if self.action == "retrieve":
            return EncomiendaDetailSerializer

        return EncomiendaSerializer

    # ── Queryset dinámico ────────────────────────────────────────
    def get_queryset(self):
        """
        v1 y v2 usan el mismo queryset optimizado.

        Si en el futuro v2 requiere más datos,
        se pueden agregar aquí.
        """
        qs = Encomienda.objects.con_relaciones()
        estado = self.request.query_params.get("estado")

        if estado:
            qs = qs.filter(estado=estado)

        # ── Búsqueda general ─────────────────────────────────────
        q = self.request.query_params.get("search")
        if q:
            qs = qs.filter(
                Q(codigo__icontains=q)
                | Q(remitente__apellidos__icontains=q)
                | Q(destinatario__apellidos__icontains=q)
            )  # type: ignore

        # ── Optimización específica para list() ─────────────────
        # only() reduce columnas SQL y mejora performance.
        if self.action == "list":
            qs = qs.only(
                # ── Campos de Encomienda ────────────────────────
                "id",
                "codigo",
                "estado",
                "peso_kg",
                "costo_envio",
                "fecha_registro",
                "fecha_entrega_est",
                # ── Remitente ──────────────────────────────────
                "remitente__nombres",
                "remitente__apellidos",
                # ── Destinatario ───────────────────────────────
                "destinatario__nombres",
                "destinatario__apellidos",
                # ── Ruta ───────────────────────────────────────
                "ruta__codigo",  # Requerido por to_representation
                "ruta__origen",  # Requerido por to_representation
                "ruta__destino",
                # ── Foreign Keys Obligatorios ──────────────────
                "empleado_registro_id",  # Necesario para evitar conflicto con select_related()
            )

        return qs

    # ── Listado con cabecera de versión ─────────────────────────
    def list(self, request, *args, **kwargs):
        """
        Agregar cabecera X-API-Version.
        """
        response = super().list(request, *args, **kwargs)
        response["X-API-Version"] = getattr(request, "version", "v1")
        return response

    # ── Detalle con cabecera de versión ─────────────────────────
    def retrieve(self, request, *args, **kwargs):
        """
        Agregar cabecera X-API-Version.
        """
        response = super().retrieve(request, *args, **kwargs)
        response["X-API-Version"] = getattr(request, "version", "v1")
        return response

    # ── Hook antes de crear ──────────────────────────────────────
    def perform_create(self, serializer):
        # Buscar empleado por el email del usuario autenticado
        empleado = Empleado.objects.get(email=self.request.user.email)
        serializer.save(empleado_registro=empleado)

    # ── Hook después de actualizar ────────────────────────────────
    def perform_update(self, serializer):
        """
        Invalidar caché al actualizar.
        """
        super().perform_update(serializer)
        # Limpiar stats del empleado solicitante
        cache_key = f"estadisticas_empleado_{self.request.user.id}"
        cache.delete(cache_key)

    # ── POST /encomiendas/{pk}/cambiar_estado/ ──────────────────

    @extend_schema(
        summary="Cambiar estado de encomienda",
        description="""
        Cambia el estado de una encomienda y registra
        automáticamente el cambio en el historial.

        Estados disponibles:
        - PE: Pendiente
        - TR: En tránsito
        - DE: En destino
        - EN: Entregado
        - DV: Devuelto
        """,
        request=OpenApiTypes.OBJECT,
        responses={
            200: EncomiendaSerializer,
            400: OpenApiResponse(description="Estado inválido o repetido."),
        },
        examples=[
            OpenApiExample(
                "Pasar a En tránsito",
                value={"estado": "TR", "observacion": "Recogido en agencia Lima"},
                request_only=True,
            ),
            OpenApiExample(
                "Marcar como entregado",
                value={"estado": "EN", "observacion": "Entregado al destinatario"},
                request_only=True,
            ),
        ],
        tags=["Encomiendas"],
    )
    @action(detail=True, methods=["post"], url_path="cambiar_estado")
    def cambiar_estado(self, request, pk=None, **kwargs):
        enc = self.get_object()
        nuevo_estado = request.data.get("estado")
        observacion = request.data.get("observacion", "")

        if not nuevo_estado:
            return Response(
                {"error": "El campo estado es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            empleado = Empleado.objects.get(email=request.user.email)
            enc.cambiar_estado(nuevo_estado, empleado, observacion)

            # ── Invalidar cachés relacionados ───────────────────────
            cache.delete_many(
                [
                    # Estadísticas del empleado
                    f"estadisticas_empleado_{request.user.id}",
                    # Detalle específico de la encomienda
                    f"encomienda_detalle_{pk}",
                ]
            )

            return Response(EncomiendaSerializer(enc).data)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ── GET /encomiendas/con_retraso/ ───────────────────────────

    @extend_schema(
        summary="Encomiendas con retraso",
        description="""
        Lista encomiendas activas cuya fecha
        estimada de entrega ya venció.
        """,
        tags=["Encomiendas"],
        responses={200: EncomiendaSerializer(many=True)},
    )
    @action(detail=False, methods=["get"], url_path="con_retraso")
    def con_retraso(self, request, **kwargs):
        qs = Encomienda.objects.con_retraso().con_relaciones()

        # Aplicar paginación explícitamente para respetar el pagination_class del viewset
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.get_serializer(qs, many=True).data)

    # ── GET /encomiendas/pendientes/ ────────────────────────────

    @extend_schema(
        summary="Encomiendas pendientes",
        description="""
        Lista todas las encomiendas
        en estado Pendiente.
        """,
        tags=["Encomiendas"],
    )
    @action(detail=False, methods=["get"])
    def pendientes(self, request, **kwargs):
        qs = Encomienda.objects.pendientes().con_relaciones()

        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        return Response(self.get_serializer(qs, many=True).data)

    # ── GET /encomiendas/{pk}/historial/ ────────────────────────

    @extend_schema(
        summary="Historial de estados",
        description="""
        Devuelve el historial de cambios
        de estado de una encomienda.

        Usa paginación limit/offset.
        """,
        parameters=[
            OpenApiParameter(
                name="limit",
                type=int,
                description="Cantidad de resultados",
                default=10,
            ),
            OpenApiParameter(
                name="offset",
                type=int,
                description="Posición inicial",
                default=0,
            ),
        ],
        tags=["Encomiendas"],
    )
    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None, **kwargs):
        enc = self.get_object()
        qs = enc.historial.select_related("empleado").order_by("-fecha_cambio")

        paginator = HistorialPagination()
        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            return paginator.get_paginated_response(
                HistorialEstadoSerializer(page, many=True).data
            )

        return Response(HistorialEstadoSerializer(qs, many=True).data)

    # ── GET /encomiendas/estadisticas/ ──────────────────────────

    @extend_schema(
        summary="Estadísticas globales",
        description="""
        Contadores generales del sistema:

        - activas
        - en tránsito
        - con retraso
        - entregadas hoy
        """,
        tags=["Encomiendas"],
        responses={200: OpenApiResponse(description="Objeto con contadores")},
    )
    @action(detail=False, methods=["get"])
    def estadisticas(self, request, **kwargs):
        """
        Estadísticas globales cargadas desde Caché (Redis).
        """
        cache_key = f"estadisticas_empleado_{request.user.id}"
        data = cache.get(cache_key)

        # ── Cache MISS ───────────────────────────────────────────
        if data is None:
            ahora = timezone.now()

            data = {
                "total_activas": Encomienda.objects.activas().count(),
                "en_transito": Encomienda.objects.en_transito().count(),
                "con_retraso": Encomienda.objects.con_retraso().count(),
                "entregadas_hoy": Encomienda.objects.filter(
                    estado="EN", fecha_entrega_real=ahora.date()
                ).count(),
                "entregadas_mes": Encomienda.objects.filter(
                    estado="EN", fecha_entrega_real__month=ahora.month
                ).count(),
            }

            # Guardar en Caché de Redis
            cache.set(cache_key, data, CACHE_TTL)

        return Response(data)

    # ── Bulk create ──────────────────────────────────────────────────

    @extend_schema(
        summary="Crear múltiples encomiendas",
        description="""
        Crea varias encomiendas en una sola petición.

        Body:
            [
                {enc1},
                {enc2},
                {enc3}
            ]
        """,
        tags=["Encomiendas"],
    )
    @action(detail=False, methods=["post"], url_path="bulk_create")
    def bulk_create(self, request, **kwargs):
        """
        POST /api/v1/encomiendas/bulk_create/

        Body:
            [{enc1}, {enc2}, {enc3}]

        Usa bulk_create para optimizar
        el INSERT masivo.
        """
        # many=True activa: EncomiendaBulkSerializer
        serializer = self.get_serializer(data=request.data, many=True)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Obtener empleado del usuario autenticado
        empleado = Empleado.objects.get(email=request.user.email)

        # Crear masivamente
        encomiendas = serializer.save(empleado_registro=empleado)

        return Response(
            self.get_serializer(encomiendas, many=True).data,
            status=status.HTTP_201_CREATED,
        )

    # ── Bulk estado ──────────────────────────────────────────────────

    @extend_schema(
        summary="Cambiar estado a múltiples encomiendas",
        description="""
        Cambia el estado de varias encomiendas.

        Reporta:
        - actualizadas
        - errores
        - ids no encontrados
        """,
        tags=["Encomiendas"],
    )
    @action(detail=False, methods=["patch"], url_path="bulk_estado")
    def bulk_estado(self, request, **kwargs):
        """
        PATCH /api/v1/encomiendas/bulk_estado/

        Body:
        {
            "ids": [1, 2, 3],
            "estado": "TR",
            "observacion": "..."
        }
        """
        ids = request.data.get("ids", [])
        nuevo_estado = request.data.get("estado")
        observacion = request.data.get("observacion", "")

        # ── Validaciones ────────────────────────────────────────────
        if not ids:
            return Response(
                {"error": "El campo ids es requerido y no puede estar vacío."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not nuevo_estado:
            return Response(
                {"error": "El campo estado es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Obtener empleado ────────────────────────────────────────
        try:
            empleado = Empleado.objects.get(email=request.user.email)
        except Empleado.DoesNotExist:
            return Response(
                {"error": "El usuario no tiene un empleado asociado."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # ── Buscar encomiendas ──────────────────────────────────────
        encomiendas = Encomienda.objects.filter(id__in=ids)

        actualizadas = []
        errores = []

        # ── Procesar una por una ────────────────────────────────────
        for enc in encomiendas:
            try:
                enc.cambiar_estado(nuevo_estado, empleado, observacion)
                actualizadas.append(enc.id)
            except ValueError as e:
                errores.append(
                    {
                        "id": enc.id,
                        "error": str(e),
                    }
                )

        # ── IDs inexistentes ────────────────────────────────────────
        ids_procesados = list(encomiendas.values_list("id", flat=True))
        no_encontrados = [i for i in ids if i not in ids_procesados]

        # ── Respuesta final ─────────────────────────────────────────
        return Response(
            {
                "actualizadas": actualizadas,
                "errores": errores,
                "no_encontrados": no_encontrados,
                "total": len(actualizadas),
            }
        )
