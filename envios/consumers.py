import json
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
    AsyncJsonWebsocketConsumer,
)
from django.utils import timezone
from channels.db import database_sync_to_async


class DashboardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return
        self.group_name = "dashboard"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.channel_layer.group_add("encomiendas_global", self.channel_name)
        await self.accept()

        # PATRON 3: ORM async nativo (Django 4.1+)
        stats = await self.get_stats_async()
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "stats_iniciales",
                    "stats": stats,
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.channel_layer.group_discard(
                "encomiendas_global", self.channel_name
            )

    async def dashboard_actualizar(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "stats_actualizado",
                    "stats": event["stats"],
                }
            )
        )

    async def encomienda_estado_cambio(self, event):
        stats = await self.get_stats_async()
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "stats_actualizado",
                    "stats": stats,
                }
            )
        )
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "estado_cambio",
                    "encomienda_id": event["encomienda_id"],
                    "codigo": event["codigo"],
                    "estado_anterior": event["estado_anterior"],
                    "estado_nuevo": event["estado_nuevo"],
                    "empleado": event["empleado"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    async def get_stats_async(self):
        """Uso de metodos async nativos (.acount())"""
        from .models import Encomienda

        hoy = timezone.now().date()
        return {
            "activas": await Encomienda.objects.activas().acount(),
            "en_transito": await Encomienda.objects.en_transito().acount(),
            "con_retraso": await Encomienda.objects.con_retraso().acount(),
            "entregadas_hoy": await Encomienda.objects.filter(
                estado="EN", fecha_entrega_real=hoy
            ).acount(),
        }


class EncomiendaConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return
        self.group_name = "encomiendas_global"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # PATRON 1: Metodo decorado con @database_sync_to_async
        stats = await self.get_estadisticas_sync()
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "conectado",
                    "usuario": user.username,
                    "stats": stats,
                }
            )
        )

    async def receive(self, text_data):
        # Siempre envolver en try/except para evitar que la conexion
        # se cierre por un error no controlado
        try:
            data = json.loads(text_data)
            await self.procesar_mensaje(data)
        except json.JSONDecodeError:
            await self.send(
                text_data=json.dumps(
                    {
                        "tipo": "error",
                        "codigo": "JSON_INVALIDO",
                        "mensaje": "El mensaje no es JSON valido",
                    }
                )
            )
        except Exception as e:
            import logging

            logger = logging.getLogger(__name__)
            logger.error(f"Error en consumer: {e}", exc_info=True)
            await self.send(
                text_data=json.dumps(
                    {
                        "tipo": "error",
                        "codigo": "ERROR_INTERNO",
                        "mensaje": "Error interno del servidor",
                    }
                )
            )

    async def procesar_mensaje(self, data):
        tipo = data.get("tipo")
        if tipo == "ping":
            await self.send(text_data=json.dumps({"tipo": "pong"}))
        elif tipo == "solicitar_stats":
            stats = await self.get_estadisticas()
            await self.send(text_data=json.dumps({"tipo": "stats", "stats": stats}))
        elif (
            tipo == "suscribir_encomienda"
        ):  # Unirse al grupo especifico de una encomienda
            enc_id = data.get("encomienda_id")
            if enc_id:
                await self.channel_layer.group_add(
                    f"encomienda_{enc_id}", self.channel_name
                )
                await self.send(
                    text_data=json.dumps({"tipo": "suscrito", "encomienda_id": enc_id})
                )
        else:
            await self.send(
                text_data=json.dumps(
                    {"tipo": "error", "mensaje": f"Tipo desconocido: {tipo}"}
                )
            )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def encomienda_estado_cambio(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "estado_cambio",
                    "encomienda_id": event["encomienda_id"],
                    "codigo": event["codigo"],
                    "estado_anterior": event["estado_anterior"],
                    "estado_nuevo": event["estado_nuevo"],
                    "empleado": event["empleado"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    @database_sync_to_async
    def get_estadisticas_sync(self):
        """PATRON 1: Funcion sincrona ejecutada en hilo separado"""
        from .models import Encomienda

        return {
            "activas": Encomienda.objects.activas().count(),
            "en_transito": Encomienda.objects.en_transito().count(),
            "con_retraso": Encomienda.objects.con_retraso().count(),
        }

    async def get_estadisticas(self):
        """Obtener estadísticas utilizando get_estadisticas_sync"""
        return await self.get_estadisticas_sync()


class EncomiendaJsonConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return
        self.group_name = "encomiendas_global"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # PATRON 3
        from .models import Encomienda

        stats = {"activas": await Encomienda.objects.activas().acount()}
        await self.send_json({"tipo": "conectado", "stats": stats})

    async def receive_json(self, content, **kwargs):
        tipo = content.get("tipo")
        if tipo == "ping":
            await self.send_json({"tipo": "pong"})
        elif tipo == "solicitar_stats":
            from .models import Encomienda

            stats = {"activas": await Encomienda.objects.activas().acount()}
            await self.send_json({"tipo": "stats", "stats": stats})

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def encomienda_estado_cambio(self, event):
        await self.send_json(
            {
                "tipo": "estado_cambio",
                "codigo": event["codigo"],
                "nuevo": event["estado_nuevo"],
            }
        )


class EncomiendaDetalleConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close(code=4001)
            return
        self.enc_pk = self.scope["url_route"]["kwargs"]["pk"]
        self.group_name = f"encomienda_{self.enc_pk}"

        # PATRON 3: aexists()
        from .models import Encomienda

        if not await Encomienda.objects.filter(pk=self.enc_pk).aexists():
            await self.close(code=4004)
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # PATRON 1: Serializacion requiere contexto sincrono usualmente
        enc_data = await self.get_encomienda_serialized(self.enc_pk)
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "estado_actual",
                    "encomienda": enc_data,
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def encomienda_estado_cambio(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "tipo": "estado_cambio",
                    "estado_anterior": event["estado_anterior"],
                    "estado_nuevo": event["estado_nuevo"],
                    "empleado": event["empleado"],
                    "timestamp": event["timestamp"],
                }
            )
        )

    @database_sync_to_async
    def get_encomienda_serialized(self, pk):
        """PATRON 1: Para logica compleja como serializadores DRF"""
        from .models import Encomienda
        from api.serializers import EncomiendaDetailSerializer

        try:
            enc = Encomienda.objects.con_relaciones().get(pk=pk)
            return dict(EncomiendaDetailSerializer(enc).data)
        except:
            return None
