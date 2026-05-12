# envios/api_views.py

from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Encomienda
from rest_framework import generics

from api.pagination import ClientePagination

from .models import Cliente, Ruta

from .serializers import (
    ClienteSerializer,
    RutaSerializer,
)

# envios/viewsets.py

from django.utils import timezone

from rest_framework import viewsets
from rest_framework.decorators import action

# Importar los paginadores del proyecto
from api.pagination import (
    EncomiendaPagination,
    HistorialPagination,
)


from .models import Empleado
from .serializers import (
    EncomiendaSerializer,
    EncomiendaDetailSerializer,
    HistorialEstadoSerializer,
)

# envios/api_views.py — Mixins

from rest_framework import mixins


class EncomiendaViewSet(viewsets.ModelViewSet):
    queryset = Encomienda.objects.con_relaciones()

    serializer_class = EncomiendaSerializer

    permission_classes = [IsAuthenticated]

    # ── Paginador principal del ViewSet ──────────────────────────

    pagination_class = EncomiendaPagination

    # ── Serializer dinámico ──────────────────────────────────────

    def get_serializer_class(self):

        if self.action == "retrieve":
            return EncomiendaDetailSerializer

        return EncomiendaSerializer

    # ── Hook antes de crear ──────────────────────────────────────

    def perform_create(self, serializer):

        serializer.save(empleado_registro=self.request.user.empleado)

    # ── POST /encomiendas/{pk}/cambiar_estado/ ──────────────────

    @action(detail=True, methods=["post"], url_path="cambiar_estado")
    def cambiar_estado(self, request, pk=None):

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

            return Response(EncomiendaSerializer(enc).data)

        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # ── GET /encomiendas/con_retraso/ ───────────────────────────

    @action(detail=False, methods=["get"], url_path="con_retraso")
    def con_retraso(self, request):

        qs = Encomienda.objects.con_retraso().con_relaciones()

        page = self.paginate_queryset(qs)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data)

    # ── GET /encomiendas/pendientes/ ────────────────────────────

    @action(detail=False, methods=["get"])
    def pendientes(self, request):

        qs = Encomienda.objects.pendientes().con_relaciones()

        page = self.paginate_queryset(qs)

        if page is not None:
            serializer = self.get_serializer(page, many=True)

            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(qs, many=True)

        return Response(serializer.data)

    # ── GET /encomiendas/{pk}/historial/ ────────────────────────

    @action(detail=True, methods=["get"], url_path="historial")
    def historial(self, request, pk=None):
        """
        GET /api/v1/encomiendas/{pk}/historial/

        GET /api/v1/encomiendas/{pk}/historial/
            ?limit=5&offset=10

        Devuelve historial paginado.
        """

        enc = self.get_object()

        qs = enc.historial.select_related("empleado").order_by("-fecha_cambio")

        # Usar paginador específico (LimitOffset)
        paginator = HistorialPagination()

        page = paginator.paginate_queryset(qs, request)

        if page is not None:
            serializer = HistorialEstadoSerializer(page, many=True)

            return paginator.get_paginated_response(serializer.data)

        serializer = HistorialEstadoSerializer(qs, many=True)

        return Response(serializer.data)

    # ── GET /encomiendas/estadisticas/ ──────────────────────────

    @action(detail=False, methods=["get"])
    def estadisticas(self, request):
        """
        GET /api/v1/encomiendas/estadisticas/

        Devuelve contadores globales.
        """

        hoy = timezone.now().date()

        return Response(
            {
                "total_activas": Encomienda.objects.activas().count(),
                "en_transito": Encomienda.objects.en_transito().count(),
                "con_retraso": Encomienda.objects.con_retraso().count(),
                "entregadas_hoy": Encomienda.objects.filter(
                    estado="EN", fecha_entrega_real=hoy
                ).count(),
            }
        )


# ── Lista y creación de encomiendas ──────────────────────────────


class EncomiendaListAPIView(APIView):
    """
    GET  /api/v1/encomiendas/
    POST /api/v1/encomiendas/
    """

    permission_classes = [IsAuthenticated]

    # ── GET: listar encomiendas ──────────────────────────────────

    def get(self, request):

        qs = Encomienda.objects.con_relaciones()

        serializer = EncomiendaSerializer(qs, many=True, context={"request": request})

        return Response(serializer.data)

    # ── POST: crear encomienda ───────────────────────────────────

    def post(self, request):

        serializer = EncomiendaSerializer(
            data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save(empleado_registro=request.user.empleado)

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ── Detalle de encomienda ────────────────────────────────────────


class EncomiendaDetailAPIView(APIView):
    """
    GET / PUT / PATCH / DELETE
    /api/v1/encomiendas/{pk}/
    """

    permission_classes = [IsAuthenticated]

    def get_object(self, pk):

        return get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)

    # ── GET: obtener detalle ─────────────────────────────────────

    def get(self, request, pk):

        enc = self.get_object(pk)

        return Response(EncomiendaDetailSerializer(enc).data)

    # ── PUT: actualización completa ──────────────────────────────

    def put(self, request, pk):

        enc = self.get_object(pk)

        serializer = EncomiendaSerializer(
            enc, data=request.data, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── PATCH: actualización parcial ─────────────────────────────

    def patch(self, request, pk):

        enc = self.get_object(pk)

        serializer = EncomiendaSerializer(
            enc, data=request.data, partial=True, context={"request": request}
        )

        if serializer.is_valid():
            serializer.save()

            return Response(serializer.data)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # ── DELETE: eliminar encomienda ──────────────────────────────

    def delete(self, request, pk):

        enc = self.get_object(pk)

        enc.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)


# envios/api_views.py — Mixins

# ── List + Create ────────────────────────────────────────────────


class EncomiendaListCreateView(
    mixins.ListModelMixin, mixins.CreateModelMixin, generics.GenericAPIView
):
    queryset = Encomienda.objects.con_relaciones()

    serializer_class = EncomiendaSerializer

    permission_classes = [IsAuthenticated]

    # ── GET: listar encomiendas ──────────────────────────────────

    def get(self, request, *args, **kwargs):

        return self.list(request, *args, **kwargs)

    # ── POST: crear encomienda ───────────────────────────────────

    def post(self, request, *args, **kwargs):

        return self.create(request, *args, **kwargs)

    # ── Hook antes del save() ────────────────────────────────────

    def perform_create(self, serializer):
        """
        Hook: se llama antes de save() en create()
        """

        serializer.save(empleado_registro=self.request.user.empleado)


# ── Retrieve + Update + Destroy ──────────────────────────────────


class EncomiendaDetailView(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    generics.GenericAPIView,
):
    queryset = Encomienda.objects.con_relaciones()

    serializer_class = EncomiendaSerializer

    permission_classes = [IsAuthenticated]

    # ── GET: obtener detalle ─────────────────────────────────────

    def get(self, request, *args, **kwargs):

        return self.retrieve(request, *args, **kwargs)

    # ── PUT: actualización completa ──────────────────────────────

    def put(self, request, *args, **kwargs):

        return self.update(request, *args, **kwargs)

    # ── PATCH: actualización parcial ─────────────────────────────

    def patch(self, request, *args, **kwargs):

        return self.partial_update(request, *args, **kwargs)

    # ── DELETE: eliminar ─────────────────────────────────────────

    def delete(self, request, *args, **kwargs):

        return self.destroy(request, *args, **kwargs)


# ── Clientes ─────────────────────────────────────────────────────


@extend_schema(
    summary="Listar clientes activos",
    description="""
    Devuelve todos los clientes con estado Activo.

    La respuesta está paginada de 20 en 20.
    """,
    tags=["Clientes"],
)
class ClienteListView(generics.ListAPIView):
    serializer_class = ClienteSerializer

    permission_classes = [IsAuthenticated]

    # 20 registros por página
    pagination_class = ClientePagination

    def get_queryset(self):

        return Cliente.objects.activos()


# ── Rutas ────────────────────────────────────────────────────────


@extend_schema(
    summary="Listar rutas activas",
    description="""
    Devuelve todas las rutas activas.

    Este endpoint no usa paginación.
    """,
    tags=["Rutas"],
)
class RutaListView(generics.ListAPIView):
    serializer_class = RutaSerializer

    permission_classes = [IsAuthenticated]

    # Las rutas son pocas:
    # deshabilitar paginación
    pagination_class = None

    def get_queryset(self):

        return Ruta.objects.activas()
