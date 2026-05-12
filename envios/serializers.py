# envios/serializers.py

from django.utils import timezone
from rest_framework import serializers

from .models import Encomienda, HistorialEstado
from clientes.models import Cliente
from rutas.models import Ruta


# ── Cliente Serializer ────────────────────────────────────────────


class ClienteSerializer(serializers.ModelSerializer):
    # @property del modelo expuesta como campo de solo lectura
    nombre_completo = serializers.ReadOnlyField()
    esta_activo = serializers.ReadOnlyField()

    class Meta:
        model = Cliente

        fields = [
            "id",
            "tipo_doc",
            "nro_doc",
            "nombres",
            "apellidos",
            "nombre_completo",
            "telefono",
            "email",
            "esta_activo",
        ]


# ── Ruta Serializer ───────────────────────────────────────────────


class RutaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ruta

        fields = [
            "id",
            "codigo",
            "origen",
            "destino",
            "precio_base",
            "dias_entrega",
            "estado",
        ]


# ── Historial Estado Serializer ───────────────────────────────────


class HistorialEstadoSerializer(serializers.ModelSerializer):
    empleado_nombre = serializers.ReadOnlyField(source="empleado.__str__")

    estado_anterior_display = serializers.CharField(
        source="get_estado_anterior_display", read_only=True
    )

    estado_nuevo_display = serializers.CharField(
        source="get_estado_nuevo_display", read_only=True
    )

    class Meta:
        model = HistorialEstado

        fields = [
            "id",
            "estado_anterior",
            "estado_anterior_display",
            "estado_nuevo",
            "estado_nuevo_display",
            "empleado_nombre",
            "observacion",
            "fecha_cambio",
        ]


# ── Bulk Serializer ──────────────────────────────────────────────

class EncomiendaBulkSerializer(serializers.ListSerializer):
    """
    Serializer para operaciones masivas.

    Se activa automáticamente cuando se usa:
        EncomiendaSerializer(many=True)

    Optimiza:
    - create()
    - update()

    usando:
    - bulk_create()
    - bulk_update()

    evitando N queries SQL.
    """

    # ── Bulk Create ──────────────────────────────────────────────

    def create(self, validated_data):
        """
        Crear múltiples encomiendas
        usando una sola query SQL.

        Sin bulk_create:
            INSERT por cada objeto

        Con bulk_create:
            1 solo INSERT masivo
        """
        encomiendas = [Encomienda(**item) for item in validated_data]
        return Encomienda.objects.bulk_create(encomiendas)

    # ── Bulk Update ──────────────────────────────────────────────

    def update(self, instances, validated_data):
        """
        Actualizar múltiples registros.

        IMPORTANTE:
        bulk_update NO dispara:
        - save()
        - signals
        """
        # Mapear instances por ID
        instance_map = {enc.id: enc for enc in instances}
        updated = []

        for item in validated_data:
            enc_id = item.pop("id", None)
            enc = instance_map.get(enc_id)

            if enc:
                for campo, valor in item.items():
                    setattr(enc, campo, valor)
                updated.append(enc)

        # Ejecutar UPDATE masivo
        if updated:
            Encomienda.objects.bulk_update(
                updated,
                [
                    "estado",
                    "observaciones",
                    "costo_envio",
                ],
            )

        return updated


# ── Encomienda Serializer ─────────────────────────────────────────


class EncomiendaSerializer(serializers.ModelSerializer):
    # ── Relaciones mediante IDs (lectura/escritura opcional directo) ─────────────
    remitente = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.activos(), required=False)
    destinatario = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), required=False
    )
    ruta = serializers.PrimaryKeyRelatedField(queryset=Ruta.objects.activas(), required=False)

    # ── Alias explícitos para escritura (congruencia con API v2) ───────────────
    remitente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="remitente", required=False
    )
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="destinatario", required=False
    )
    ruta_id = serializers.PrimaryKeyRelatedField(
        queryset=Ruta.objects.activas(), write_only=True, source="ruta", required=False
    )

    # ── Propiedades del modelo
    # Estos campos SON la causa del N+1:
    # ESTOS son los que causan N+1 si no hay select_related:
    # Al serializar, DRF accede a: enc.remitente, enc.destinatario,
    # enc.ruta, enc.empleado_registro -> 4 queries extra por objeto

    esta_entregada = serializers.ReadOnlyField()  # accede al modelo
    tiene_retraso = serializers.ReadOnlyField()  # accede al modelo
    dias_en_transito = serializers.ReadOnlyField()
    descripcion_corta = serializers.ReadOnlyField()  # accede al modelo
    estado_display = serializers.SerializerMethodField()

    class Meta:
        model = Encomienda
        list_serializer_class = EncomiendaBulkSerializer
        fields = [
            "id",
            "codigo",
            "descripcion",
            "peso_kg",
            "remitente",
            "destinatario",
            "ruta",
            "estado",
            "costo_envio",
            "remitente_id",
            "destinatario_id",
            "ruta_id",
            "fecha_registro",
            "fecha_entrega_est",
            "fecha_entrega_real",
            "esta_entregada",
            "tiene_retraso",
            "dias_en_transito",
            "descripcion_corta",
            "estado_display",
            "observaciones",
        ]
        read_only_fields = [
            "codigo",
            "fecha_registro",
            "fecha_entrega_real",
        ]

    # ── Validadores de campo individuales
    def validate_codigo(self, value):
        if not value.startswith("ENC-"):
            raise serializers.ValidationError("El código debe comenzar con ENC-")
        return value.upper()

    def validate_costo_envio(self, value):
        if value < 0:
            raise serializers.ValidationError("El costo no puede ser negativo.")
        return value

    # ── Validación cruzada: validate()
    def validate(self, data):
        errors = {}

        # Validar presencia de campos críticos (ahora que los campos individuales son required=False por flexibilidad)
        if not data.get("remitente"):
            errors["remitente"] = "El campo remitente o remitente_id es requerido."
        if not data.get("destinatario"):
            errors["destinatario"] = "El campo destinatario o destinatario_id es requerido."
        if not data.get("ruta"):
            errors["ruta"] = "El campo ruta o ruta_id es requerido."

        # Si faltan fundamentales, abortamos aquí antes de cruzar lógica
        if errors:
            raise serializers.ValidationError(errors)

        # Regla 1: remitente != destinatario
        if data.get("remitente") == data.get("destinatario"):
            errors["destinatario"] = (
                "El destinatario no puede ser el mismo que el remitente."
            )

        # Regla 2: fecha estimada no en el pasado
        fecha_est = data.get("fecha_entrega_est")
        if fecha_est and fecha_est < timezone.now().date():
            errors["fecha_entrega_est"] = "La fecha estimada no puede ser en el pasado."

        # Regla 3: costo mínimo según la ruta
        ruta = data.get("ruta")
        costo = data.get("costo_envio")

        # Verificamos existencia de ambos antes de comparar
        if ruta and costo and costo < float(ruta.precio_base):
            errors["costo_envio"] = (
                f"El costo mínimo para esta ruta es S/ {ruta.precio_base}."
            )

        if errors:
            raise serializers.ValidationError(errors)

        return data

    # ── Estado legible ───────────────────────────────────────────

    def get_estado_display(self, obj):
        return obj.get_estado_display()

    # ── Personalizar salida JSON ─────────────────────────────────

    def to_representation(self, instance):
        """
        Se ejecuta al serializar:
            objeto -> JSON

        Permite modificar la respuesta final.
        """
        data = super().to_representation(instance)

        # ── 1. Datos rápidos de la ruta ──────────────────────────
        # Evita requests adicionales desde frontend
        if instance.ruta_id:
            data["ruta_codigo"] = instance.ruta.codigo
            data["ruta_destino"] = instance.ruta.destino
            data["ruta_origen"] = instance.ruta.origen

        # ── 2. Formato visual del costo ──────────────────────────
        data["costo_display"] = f"S/ {instance.costo_envio:.2f}"

        # ── 3. Ocultar datos sensibles ───────────────────────────
        # Usuarios normales:
        # - no ven observaciones internas
        # - no ven empleado_registro
        request = self.context.get("request")
        if request and not request.user.is_staff:
            data.pop("observaciones", None)
            data.pop("empleado_registro", None)

        # ── 4. Indicador visual de estado ────────────────────────
        colores = {
            "PE": "gray",
            "TR": "blue",
            "DE": "orange",
            "EN": "green",
            "DV": "red",
        }
        data["estado_color"] = colores.get(instance.estado, "gray")

        return data

    # ── Normalizar datos entrantes ──────────────────────────────

    def to_internal_value(self, data):
        """
        Se ejecuta al deserializar:
            JSON -> objeto Python

        Permite limpiar y normalizar datos
        ANTES de las validaciones.
        """

        # ── Crear copia mutable ──────────────────────────────────
        if hasattr(data, "_mutable"):
            data._mutable = True

        data = data.copy() if hasattr(data, "copy") else dict(data)

        # ── 1. Normalizar código ─────────────────────────────────
        # enc-2026-001 -> ENC-2026-001
        if "codigo" in data and data["codigo"]:
            data["codigo"] = str(data["codigo"]).upper().strip()

        # ── 2. Limpiar descripción ───────────────────────────────
        if "descripcion" in data and data["descripcion"]:
            data["descripcion"] = str(data["descripcion"]).strip()

        # ── 3. Normalizar costo ──────────────────────────────────
        # 25 -> 25.00
        if "costo_envio" in data and data["costo_envio"]:
            try:
                from decimal import (
                    Decimal,
                    ROUND_HALF_UP,
                )

                costo = Decimal(str(data["costo_envio"]))
                data["costo_envio"] = str(
                    costo.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                )
            except Exception:
                # Si falla, DRF validará después
                pass

        return super().to_internal_value(data)


class EncomiendaListSerializer(EncomiendaSerializer):
    """
    Serializer simplificado para listados v1.
    No incluye descripcion larga, observaciones ni historial.
    """

    remitente_nombre = serializers.ReadOnlyField(source="remitente.nombre_completo")
    destinatario_nombre = serializers.ReadOnlyField(source="destinatario.nombre_completo")
    ruta_destino = serializers.ReadOnlyField(source="ruta.destino")
    estado_display = serializers.SerializerMethodField()
    tiene_retraso = serializers.ReadOnlyField()

    class Meta:
        model = Encomienda
        fields = [
            "id",
            "codigo",
            "estado",
            "estado_display",
            "remitente_nombre",
            "destinatario_nombre",
            "ruta_destino",
            "peso_kg",
            "costo_envio",
            "fecha_registro",
            "fecha_entrega_est",
            "tiene_retraso",
        ]

    def get_estado_display(self, obj):
        return obj.get_estado_display()


# envios/serializers.py — Serializer anidado completo


class EncomiendaDetailSerializer(serializers.ModelSerializer):
    """
    Para GET:
        devuelve objetos anidados completos

    Para POST/PUT/PATCH:
        acepta solo IDs (write_only)
    """

    # ── Campos de solo lectura: objetos anidados completos ───────

    remitente = ClienteSerializer(read_only=True)

    destinatario = ClienteSerializer(read_only=True)

    ruta = RutaSerializer(read_only=True)

    # ── Campos de solo escritura: aceptar IDs ────────────────────

    remitente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="remitente"
    )

    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="destinatario"
    )

    ruta_id = serializers.PrimaryKeyRelatedField(
        queryset=Ruta.objects.activas(), write_only=True, source="ruta"
    )

    # ── Historial: últimos 5 cambios de estado ───────────────────

    historial = serializers.SerializerMethodField()

    # ── Propiedades del modelo ───────────────────────────────────

    esta_entregada = serializers.ReadOnlyField()

    tiene_retraso = serializers.ReadOnlyField()

    dias_en_transito = serializers.ReadOnlyField()

    class Meta:
        model = Encomienda

        fields = [
            "id",
            "codigo",
            "descripcion",
            "peso_kg",
            "remitente",
            "remitente_id",
            "destinatario",
            "destinatario_id",
            "ruta",
            "ruta_id",
            "estado",
            "costo_envio",
            "fecha_registro",
            "fecha_entrega_est",
            "fecha_entrega_real",
            "esta_entregada",
            "tiene_retraso",
            "dias_en_transito",
            "historial",
            "observaciones",
        ]

    def get_historial(self, obj):
        """
        Devuelve los últimos 5 cambios de estado
        """

        return HistorialEstadoSerializer(obj.historial.all()[:5], many=True).data


# ── EncomiendaV2Serializer ────────────────────────────────────────


class EncomiendaV2Serializer(serializers.ModelSerializer):
    """
    Serializer para la API v2.

    Diferencias con v1:
    - remitente y destinatario como objetos anidados
    - ruta como objeto anidado
    - campos de análisis adicionales
    - campo meta con información de versión
    """

    # ── Objetos anidados completos ───────────────────────────────
    remitente = ClienteSerializer(read_only=True)
    destinatario = ClienteSerializer(read_only=True)
    ruta = RutaSerializer(read_only=True)

    # ── Para escritura: aceptar IDs ──────────────────────────────
    remitente_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="remitente"
    )
    destinatario_id = serializers.PrimaryKeyRelatedField(
        queryset=Cliente.objects.activos(), write_only=True, source="destinatario"
    )
    ruta_id = serializers.PrimaryKeyRelatedField(
        queryset=Ruta.objects.activas(), write_only=True, source="ruta"
    )

    # ── Campos nuevos en v2 ──────────────────────────────────────
    dias_en_transito = serializers.ReadOnlyField()
    tiene_retraso = serializers.ReadOnlyField()
    esta_entregada = serializers.ReadOnlyField()
    descripcion_corta = serializers.ReadOnlyField()

    # ── Metadatos de versión ─────────────────────────────────────
    meta = serializers.SerializerMethodField()

    class Meta:
        model = Encomienda
        fields = [
            "id",
            "codigo",
            "descripcion",
            "descripcion_corta",
            "peso_kg",
            "volumen_cm3",
            "costo_envio",
            "remitente",
            "remitente_id",
            "destinatario",
            "destinatario_id",
            "ruta",
            "ruta_id",
            "estado",
            "fecha_registro",
            "fecha_entrega_est",
            "dias_en_transito",
            "tiene_retraso",
            "esta_entregada",
            "observaciones",
            "meta",
        ]
        read_only_fields = [
            "codigo",
            "fecha_registro",
        ]

    # ── Metadatos para clientes API ──────────────────────────────
    def get_meta(self, obj):
        """
        Información útil para consumidores
        de la API v2.
        """
        from django.utils import timezone

        return {
            "version": "v2",
            "generado": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "puede_editar": not obj.esta_entregada,
        }
