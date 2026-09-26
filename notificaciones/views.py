from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.timesince import timesince
from django.views.decorators.http import require_GET, require_POST

from .models import Notificacion

LIMITE = 30


def _serializar(n, usuario, leidas_ids):
    ahora = timezone.now()
    hace = 'recién' if (ahora - n.creada).total_seconds() < 60 else f'hace {timesince(n.creada, ahora).split(",")[0]}'
    return {
        'id': n.id,
        'titulo': n.titulo,
        'mensaje': n.mensaje,
        'url': n.url,
        'icono': n.icono,
        'nivel': n.nivel,
        'modulo': n.modulo,
        'hace': hace,
        'leida': n.id in leidas_ids,
    }


@login_required(login_url='login')
@require_GET
def listar(request):
    qs = Notificacion.objects.para_usuario(request.user)
    leidas_ids = set(request.user.notificaciones_leidas.values_list('id', flat=True))
    no_leidas = qs.exclude(id__in=leidas_ids).count()
    items = [_serializar(n, request.user, leidas_ids) for n in qs[:LIMITE]]
    return JsonResponse({'no_leidas': no_leidas, 'items': items})


@login_required(login_url='login')
@require_POST
def marcar_leida(request, notificacion_id):
    n = get_object_or_404(Notificacion.objects.para_usuario(request.user), id=notificacion_id)
    n.leida_por.add(request.user)
    return JsonResponse({'ok': True})


@login_required(login_url='login')
@require_POST
def marcar_todas(request):
    pendientes = Notificacion.objects.para_usuario(request.user).exclude(leida_por=request.user)
    for n in pendientes:
        n.leida_por.add(request.user)
    return JsonResponse({'ok': True})
