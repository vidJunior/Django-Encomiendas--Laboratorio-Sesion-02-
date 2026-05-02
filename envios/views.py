from django.contrib import messages
from django.utils import timezone
from .models import Encomienda, Empleado

from config.choices import EstadoEnvio
from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


# get_object_or_404() — buscar o devolver 404
from django.shortcuts import get_object_or_404

# get_list_or_404() — lista o devolver 404
from django.shortcuts import get_list_or_404


from django.views.decorators.http import (
    require_http_methods,
)

from django.contrib.auth.decorators import (
    permission_required,
    user_passes_test,
)


# ── Vista real: dashboard del sistema ────────────────────────
@login_required
def dashboard(request):
    """Vista principal del sistema con estadísticas"""
    hoy = timezone.now().date()
    context = {
        "total_activas": Encomienda.objects.activas().count(),
        "en_transito": Encomienda.objects.en_transito().count(),
        "con_retraso": Encomienda.objects.con_retraso().count(),
        "entregadas_hoy": Encomienda.objects.filter(
            estado=EstadoEnvio.ENTREGADO, fecha_entrega_real=hoy
        ).count(),
        "ultimas": Encomienda.objects.con_relaciones()[:5],
    }

    return render(request, "envios/dashboard.html", context)


# GET y POST
# Requiere un permiso específico del sistema de permisos de Django
@permission_required("envios.add_encomienda", raise_exception=True)
@require_http_methods(["GET", "POST"])
@login_required
def encomienda_crear(request):
    """
    GET → muestra el formulario vacío
    POST → valida, guarda y redirige al detalle
    """
    from .forms import EncomiendaForm

    if request.method == "POST":
        form = EncomiendaForm(request.POST)

        if form.is_valid():
            enc = form.save(commit=False)  # no guarda aún en BD

            enc.empleado_registro = Empleado.objects.get(email=request.user.email)

            enc.save()  # ahora sí guarda

            messages.success(
                request, f"Encomienda {enc.codigo} registrada correctamente."
            )

            # Redirige para evitar reenvío del formulario al recargar
            return redirect("encomienda_detalle", pk=enc.pk)

        else:
            messages.error(request, "Corrige los errores del formulario.")

        # Si el form tiene errores, cae aquí y se vuelve a renderizar

    else:
        form = EncomiendaForm()  # GET: form vacío

    return render(
        request,
        "envios/form.html",
        {
            "form": form,
            "titulo": "Nueva Encomienda",
        },
    )


# redirect() — redirigir a otra URL
def mi_vista(request):
    # Redirigir por nombre de URL
    return redirect("encomienda_lista")

    # Redirigir con argumento (ejemplo)
    return redirect("encomienda_detalle", pk=1)
    return redirect("/encomiendas/")


def encomienda_detalle(request, pk):
    """
    Vista de detalle de una encomienda.
    Si no existe el pk → devuelve 404 automáticamente.
    """

    # Opción simple
    enc = get_object_or_404(Encomienda, pk=pk)

    # Opción optimizada (si tienes un manager/queryset personalizado)
    # enc = get_object_or_404(Encomienda.objects.con_relaciones(), pk=pk)

    return render(request, "envios/detalle.html", {"encomienda": enc})


def encomiendas_por_ruta(request, ruta_pk):
    """
    Lista de encomiendas por ruta.
    Si no hay resultados → devuelve 404 automáticamente.
    """

    encomiendas = get_list_or_404(Encomienda, ruta__pk=ruta_pk)

    return render(
        request,
        "envios/lista.html",
        {
            "encomiendas": encomiendas,
        },
    )


def encomienda_lista(request):
    estado = request.GET.get("estado", "")  # '' si no existe
    q = request.GET.get("q", "")
    # page = request.GET.get("page", 1)

    qs = Encomienda.objects.con_relaciones()

    if estado:
        qs = qs.filter(estado=estado)

    from django.db.models import Q

    if q:
        qs = qs.filter(
            Q(codigo__icontains=q)
            | Q(remitente__apellidos__icontains=q)
            | Q(destinatario__apellidos__icontains=q)
        )

    return render(
        request,
        "envios/lista.html",
        {
            "encomiendas": qs,
        },
    )


@login_required
def encomienda_cambiar_estado(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)

    if request.method == "POST":
        nuevo_estado = request.POST.get("estado")
        observacion = request.POST.get("observacion", "")

        try:
            empleado = Empleado.objects.get(email=request.user.email)

            enc.cambiar_estado(nuevo_estado, empleado, observacion)

            messages.success(
                request, f"Estado actualizado a: {enc.get_estado_display()}"
            )

        except ValueError as e:
            messages.error(request, str(e))

    return redirect("encomienda_detalle", pk=pk)


# Condición personalizada para el sistema de encomiendas
def es_empleado_activo(user):
    """True si el user tiene un Empleado activo asociado"""
    return (
        user.is_authenticated
        and Empleado.objects.filter(email=user.email, estado=1).exists()
    )


@user_passes_test(es_empleado_activo, login_url="/sin-permiso/")
def registrar_envio(request): ...


@login_required
def eliminar_encomienda(request, pk):
    enc = get_object_or_404(Encomienda, pk=pk)
    # Solo se puede eliminar si está pendiente (lógica de negocio)
    # Verificar permisos manualmente dentro de la vista
    from django.core.exceptions import PermissionDenied

    if enc.estado != "PE":
        raise PermissionDenied  # → devuelve 403 Forbidden
    if request.method == "POST":
        enc.delete()
        messages.success(request, "Encomienda eliminada.")
        return redirect("encomienda_lista")
    return render(request, "envios/confirmar_eliminar.html", {"enc": enc})


@login_required
def buscar_por_codigo(request, codigo):
    """Busca una encomienda por su código exacto"""
    enc = get_object_or_404(Encomienda, codigo=codigo)
    return redirect("encomienda_detalle", pk=enc.pk)
