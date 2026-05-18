import asyncio
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from .models import Encomienda

async def dashboard_stats_async(request):
    """
    Endpoint async que calcula las estadísticas del dashboard.
    
    Lab 1: Dashboard con 4 queries en paralelo.
    Reemplaza el dashboard síncrono por uno async.
    
    Comparativa de rendimiento:
    - ANTES (síncrono): 4 queries secuenciales = 4 * 10ms = 40ms
    - AHORA (async): 4 queries en paralelo = max(10ms) = 10ms
    """
    if not request.user.is_authenticated:
        return HttpResponse(status=401)

    hoy = timezone.now().date()

    # Las 4 queries corren EN PARALELO
    # gather espera a que TODAS terminen
    activas, en_transito, con_retraso, entregadas_hoy = await asyncio.gather(
        Encomienda.objects.activas().acount(),
        Encomienda.objects.en_transito().acount(),
        Encomienda.objects.con_retraso().acount(),
        Encomienda.objects.filter(
            estado='EN',
            fecha_entrega_real=hoy
        ).acount(),
    )

    return JsonResponse({
        'activas': activas,
        'en_transito': en_transito,
        'con_retraso': con_retraso,
        'entregadas_hoy': entregadas_hoy,
    })
