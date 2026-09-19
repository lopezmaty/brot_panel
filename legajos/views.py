import base64
import json
from functools import lru_cache

from django.contrib.auth.decorators import login_required
from django.contrib.staticfiles import finders
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from weasyprint import HTML

from .models import Ausencia, DocumentacionEmpleado, DocumentoPersonal, Empleado, Novedad


def _es_admin(request):
    perfil = getattr(request.user, "perfil", None)
    return bool(perfil and perfil.rol == "admin")


def _puede_ver(request):
    perfil = getattr(request.user, "perfil", None)
    return bool(perfil and perfil.rol in ("admin", "colab"))


@login_required
def legajos_view(request):
    if not _puede_ver(request):
        return HttpResponseForbidden("No tenés permiso para ver esta sección.")
    return render(request, "legajos/legajos.html", {"es_admin": _es_admin(request)})


# ── Serialización ────────────────────────────────────────────────────────────

def _empleado_to_dict(emp):
    return {
        "id": emp.id,
        "nombre": emp.nombre,
        "apellido": emp.apellido,
        "nombre_completo": emp.nombre_completo,
        "iniciales": emp.iniciales,
        "dni": emp.dni,
        "cuil": emp.cuil,
        "fecha_nacimiento": emp.fecha_nacimiento.isoformat() if emp.fecha_nacimiento else None,
        "domicilio": emp.domicilio,
        "telefono": emp.telefono,
        "email": emp.email,
        "puesto": emp.puesto,
        "fecha_ingreso": emp.fecha_ingreso.isoformat() if emp.fecha_ingreso else None,
        "fecha_baja": emp.fecha_baja.isoformat() if emp.fecha_baja else None,
        "estado": emp.estado,
    }


_BADGE_DOC = {
    DocumentoPersonal.Estado.BORRADOR: ("borrador", "Borrador"),
    DocumentoPersonal.Estado.GENERADO: ("pendiente", "Pendiente de firma"),
    DocumentoPersonal.Estado.FIRMADO: ("firmado", "Firmado"),
}

_BADGE_VENCIMIENTO = {
    "vigente": ("firmado", "Vigente"),
    "por_vencer": ("pendiente", "Por vencer"),
    "vencido": ("vencido", "Vencido"),
    "sin_vencimiento": ("borrador", "Sin vencimiento"),
}


def _historial_empleado(emp):
    """Junta documentos, ausencias y documentación con vencimiento en una
    sola línea de tiempo. Los módulos de Trámites/Documentación/Ausencias
    van a reusar estos mismos datos cuando se armen sus propias pestañas.
    """
    items = []

    for doc in emp.documentos.all():
        badge, badge_label = _BADGE_DOC.get(doc.estado, ("borrador", doc.get_estado_display()))
        texto = doc.get_tipo_display()
        if doc.motivo:
            texto += f" — {doc.motivo[:60]}"
        items.append({"fecha": doc.fecha.isoformat(), "texto": texto, "badge": badge, "badge_label": badge_label})

    for aus in emp.ausencias.all():
        badge, badge_label = ("firmado", "Justificada") if aus.justificada else ("vencido", "Injustificada")
        texto = f"Ausencia: {aus.get_tipo_display()} ({aus.fecha_desde:%d/%m} al {aus.fecha_hasta:%d/%m})"
        items.append({"fecha": aus.fecha_desde.isoformat(), "texto": texto, "badge": badge, "badge_label": badge_label})

    hoy = timezone.localdate()
    for doc in emp.documentacion.all():
        estado = doc.estado_vencimiento(hoy)
        badge, badge_label = _BADGE_VENCIMIENTO[estado]
        texto = doc.get_tipo_display()
        if doc.fecha_vencimiento:
            texto += f" — vence {doc.fecha_vencimiento:%d/%m/%Y}"
        fecha_orden = doc.fecha_vencimiento or doc.creado_en.date()
        items.append({"fecha": fecha_orden.isoformat(), "texto": texto, "badge": badge, "badge_label": badge_label})

    items.sort(key=lambda i: i["fecha"], reverse=True)
    return items


# ── API: listado y alta ───────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "POST"])
def api_empleados(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    if request.method == "GET":
        qs = Empleado.objects.all()

        estado = request.GET.get("estado")
        if estado:
            qs = qs.filter(estado=estado)

        busqueda = request.GET.get("q", "").strip()
        if busqueda:
            qs = qs.filter(
                Q(nombre__icontains=busqueda) | Q(apellido__icontains=busqueda) | Q(dni__icontains=busqueda)
            )

        return JsonResponse({"empleados": [_empleado_to_dict(e) for e in qs]})

    # POST → alta, solo admin
    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede crear empleados.")

    data = json.loads(request.body)
    if not data.get("nombre") or not data.get("apellido") or not data.get("dni"):
        return JsonResponse({"error": "Nombre, apellido y DNI son obligatorios."}, status=400)
    if Empleado.objects.filter(dni=data["dni"]).exists():
        return JsonResponse({"error": "Ya existe un empleado con ese DNI."}, status=400)

    emp = Empleado.objects.create(
        nombre=data["nombre"],
        apellido=data["apellido"],
        dni=data["dni"],
        cuil=data.get("cuil", ""),
        fecha_nacimiento=data.get("fecha_nacimiento") or None,
        domicilio=data.get("domicilio", ""),
        telefono=data.get("telefono", ""),
        email=data.get("email", ""),
        puesto=data.get("puesto", ""),
        fecha_ingreso=data.get("fecha_ingreso") or timezone.localdate(),
        estado=data.get("estado") or Empleado.Estado.ACTIVO,
    )
    return JsonResponse(_empleado_to_dict(emp), status=201)


# ── API: detalle, edición y baja ──────────────────────────────────────────────

@login_required
@require_http_methods(["GET", "PUT", "DELETE"])
def api_empleado_detail(request, pk):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    emp = get_object_or_404(Empleado, pk=pk)

    if request.method == "GET":
        payload = _empleado_to_dict(emp)
        payload["historial"] = _historial_empleado(emp)
        return JsonResponse(payload)

    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede editar o dar de baja empleados.")

    if request.method == "PUT":
        data = json.loads(request.body)
        for campo in ["nombre", "apellido", "cuil", "domicilio", "telefono", "email", "puesto"]:
            if campo in data:
                setattr(emp, campo, data[campo])
        if "fecha_nacimiento" in data:
            emp.fecha_nacimiento = data["fecha_nacimiento"] or None
        if "fecha_ingreso" in data and data["fecha_ingreso"]:
            emp.fecha_ingreso = data["fecha_ingreso"]
        if "dni" in data and data["dni"] != emp.dni:
            if Empleado.objects.filter(dni=data["dni"]).exclude(pk=emp.pk).exists():
                return JsonResponse({"error": "Ya existe un empleado con ese DNI."}, status=400)
            emp.dni = data["dni"]
        emp.save()
        return JsonResponse(_empleado_to_dict(emp))

    # DELETE → no borra el registro (se pierde el historial), lo pasa a inactivo.
    emp.estado = Empleado.Estado.INACTIVO
    emp.fecha_baja = timezone.localdate()
    emp.save(update_fields=["estado", "fecha_baja"])
    return JsonResponse({"ok": True})


# ── Documentación (carnet manipulación, credencial ART, etc.) ────────────────

def _documentacion_to_dict(doc, hoy):
    estado = doc.estado_vencimiento(hoy)
    badge, badge_label = _BADGE_VENCIMIENTO[estado]
    tipo_label = doc.get_tipo_display()
    if doc.tipo == DocumentacionEmpleado.Tipo.OTRO and doc.tipo_otro_detalle:
        tipo_label = doc.tipo_otro_detalle
    return {
        "id": doc.id,
        "empleado_id": doc.empleado_id,
        "empleado_nombre": doc.empleado.nombre_completo,
        "tipo": doc.tipo,
        "tipo_label": tipo_label,
        "fecha_emision": doc.fecha_emision.isoformat() if doc.fecha_emision else None,
        "fecha_vencimiento": doc.fecha_vencimiento.isoformat() if doc.fecha_vencimiento else None,
        "estado": estado,
        "badge": badge,
        "badge_label": badge_label,
        "archivo_url": doc.archivo.url if doc.archivo else None,
    }


@login_required
@require_http_methods(["GET", "POST"])
def api_documentacion(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    if request.method == "GET":
        qs = DocumentacionEmpleado.objects.select_related("empleado").all()
        empleado_id = request.GET.get("empleado")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        hoy = timezone.localdate()
        items = [_documentacion_to_dict(d, hoy) for d in qs]
        estado = request.GET.get("estado")
        if estado:
            items = [i for i in items if i["estado"] == estado]
        return JsonResponse({"documentacion": items})

    # POST → alta, solo admin. Viene como multipart (hay un archivo), no JSON.
    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede subir documentación.")

    empleado_id = request.POST.get("empleado")
    tipo = request.POST.get("tipo")
    archivo = request.FILES.get("archivo")
    if not empleado_id or not tipo or not archivo:
        return JsonResponse({"error": "Empleado, tipo y archivo son obligatorios."}, status=400)

    empleado = get_object_or_404(Empleado, pk=empleado_id)
    doc = DocumentacionEmpleado.objects.create(
        empleado=empleado,
        tipo=tipo,
        tipo_otro_detalle=request.POST.get("tipo_otro_detalle", ""),
        archivo=archivo,
        fecha_emision=request.POST.get("fecha_emision") or None,
        fecha_vencimiento=request.POST.get("fecha_vencimiento") or None,
    )
    return JsonResponse(_documentacion_to_dict(doc, timezone.localdate()), status=201)


@login_required
@require_http_methods(["DELETE"])
def api_documentacion_detail(request, pk):
    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede eliminar documentación.")
    doc = get_object_or_404(DocumentacionEmpleado, pk=pk)
    doc.archivo.delete(save=False)
    doc.delete()
    return JsonResponse({"ok": True})


# ── Trámites y firmas (legajo inicial, apercibimientos, cambios de domicilio…) ─

def _documento_to_dict(doc):
    badge, _ = _BADGE_DOC.get(doc.estado, ("borrador", None))
    return {
        "id": doc.id,
        "empleado_id": doc.empleado_id,
        "empleado_nombre": doc.empleado.nombre_completo,
        "tipo": doc.tipo,
        "tipo_label": doc.get_tipo_display(),
        "fecha": doc.fecha.isoformat(),
        "motivo": doc.motivo,
        "domicilio_nuevo": doc.domicilio_nuevo,
        "estado": doc.estado,
        "badge": badge,
        "badge_label": doc.get_estado_display(),
        "pdf_url": doc.pdf_generado.url if doc.pdf_generado else None,
        "firmado_url": doc.archivo_firmado.url if doc.archivo_firmado else None,
    }


def _generar_pdf_documento(doc):
    """Arma el PDF a partir de la plantilla legajos/documento_pdf.html y lo
    deja guardado en doc.pdf_generado (mismo motor, WeasyPrint, que ya usás
    para exportar la lista de precios)."""
    html_string = render_to_string(
        "legajos/documento_pdf.html", {"doc": doc, "logo_base64": _logo_base64()}
    )
    pdf_bytes = HTML(string=html_string).write_pdf()
    nombre_archivo = f"{doc.tipo}_{doc.empleado.dni}_{doc.fecha}.pdf"
    doc.pdf_generado.save(nombre_archivo, ContentFile(pdf_bytes), save=False)


@lru_cache(maxsize=1)
def _logo_base64():
    """Toma el mismo logo que ya usa base.html en el topnav (static/img/logo.png)
    y lo devuelve codificado en base64, para incrustarlo directo en el PDF.
    WeasyPrint no resuelve {% static %} solo, así que se lo pasamos como
    data URI. Se cachea porque el archivo no cambia en caliente."""
    path = finders.find("img/logo.png")
    if not path:
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


@login_required
@require_http_methods(["GET", "POST"])
def api_documentos(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    if request.method == "GET":
        qs = DocumentoPersonal.objects.select_related("empleado").all()
        empleado_id = request.GET.get("empleado")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        tipo = request.GET.get("tipo")
        if tipo:
            qs = qs.filter(tipo=tipo)
        return JsonResponse({"documentos": [_documento_to_dict(d) for d in qs]})

    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede generar trámites.")

    data = json.loads(request.body)
    empleado_id = data.get("empleado")
    tipo = data.get("tipo")
    if not empleado_id or not tipo:
        return JsonResponse({"error": "Empleado y tipo son obligatorios."}, status=400)
    empleado = get_object_or_404(Empleado, pk=empleado_id)

    doc = DocumentoPersonal.objects.create(
        empleado=empleado,
        tipo=tipo,
        fecha=data.get("fecha") or timezone.localdate(),
        motivo=data.get("motivo", ""),
        domicilio_nuevo=data.get("domicilio_nuevo", ""),
        creado_por=request.user,
    )
    _generar_pdf_documento(doc)
    doc.estado = DocumentoPersonal.Estado.GENERADO
    doc.save()
    return JsonResponse(_documento_to_dict(doc), status=201)


@login_required
@require_http_methods(["POST"])
def api_documento_firmar(request, pk):
    """Recibe el escaneo/foto del documento ya firmado en papel. El propio
    DocumentoPersonal.save() se encarga de pasar el estado a 'firmado' y,
    si es un cambio de domicilio, actualizar el domicilio del empleado."""
    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede subir el firmado.")
    doc = get_object_or_404(DocumentoPersonal, pk=pk)
    archivo = request.FILES.get("archivo_firmado")
    if not archivo:
        return JsonResponse({"error": "Falta el archivo firmado."}, status=400)
    doc.archivo_firmado = archivo
    doc.save()
    return JsonResponse(_documento_to_dict(doc))


# ── Ausencias ──────────────────────────────────────────────────────────────

def _ausencia_to_dict(a):
    return {
        "id": a.id,
        "empleado_id": a.empleado_id,
        "empleado_nombre": a.empleado.nombre_completo,
        "fecha_desde": a.fecha_desde.isoformat(),
        "fecha_hasta": a.fecha_hasta.isoformat(),
        "tipo": a.tipo,
        "tipo_label": a.get_tipo_display(),
        "justificada": a.justificada,
        "certificado_url": a.certificado.url if a.certificado else None,
        "observaciones": a.observaciones,
    }


@login_required
@require_http_methods(["GET", "POST"])
def api_ausencias(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    if request.method == "GET":
        qs = Ausencia.objects.select_related("empleado").all()
        empleado_id = request.GET.get("empleado")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        return JsonResponse({"ausencias": [_ausencia_to_dict(a) for a in qs]})

    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede registrar ausencias.")

    empleado_id = request.POST.get("empleado")
    fecha_desde = request.POST.get("fecha_desde")
    fecha_hasta = request.POST.get("fecha_hasta")
    tipo = request.POST.get("tipo")
    if not empleado_id or not fecha_desde or not fecha_hasta or not tipo:
        return JsonResponse({"error": "Empleado, fechas y tipo son obligatorios."}, status=400)

    empleado = get_object_or_404(Empleado, pk=empleado_id)
    aus = Ausencia.objects.create(
        empleado=empleado,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        tipo=tipo,
        justificada=request.POST.get("justificada") == "true",
        certificado=request.FILES.get("certificado"),
        observaciones=request.POST.get("observaciones", ""),
    )
    return JsonResponse(_ausencia_to_dict(aus), status=201)


@login_required
@require_http_methods(["DELETE"])
def api_ausencia_detail(request, pk):
    if not _es_admin(request):
        return HttpResponseForbidden()
    aus = get_object_or_404(Ausencia, pk=pk)
    if aus.certificado:
        aus.certificado.delete(save=False)
    aus.delete()
    return JsonResponse({"ok": True})


# ── Novedades ──────────────────────────────────────────────────────────────

def _novedad_to_dict(n):
    return {
        "id": n.id,
        "empleado_id": n.empleado_id,
        "empleado_nombre": n.empleado.nombre_completo if n.empleado else "General",
        "fecha": n.fecha.isoformat(),
        "tipo": n.tipo,
        "tipo_label": n.get_tipo_display(),
        "texto": n.texto,
    }


@login_required
@require_http_methods(["GET", "POST"])
def api_novedades(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    if request.method == "GET":
        qs = Novedad.objects.select_related("empleado").all()
        empleado_id = request.GET.get("empleado")
        if empleado_id:
            qs = qs.filter(empleado_id=empleado_id)
        return JsonResponse({"novedades": [_novedad_to_dict(n) for n in qs]})

    if not _es_admin(request):
        return HttpResponseForbidden("Solo un administrador puede cargar novedades.")

    data = json.loads(request.body)
    if not data.get("texto"):
        return JsonResponse({"error": "El texto es obligatorio."}, status=400)

    empleado = None
    if data.get("empleado"):
        empleado = get_object_or_404(Empleado, pk=data["empleado"])

    nov = Novedad.objects.create(
        empleado=empleado,
        fecha=data.get("fecha") or timezone.localdate(),
        tipo=data.get("tipo") or Novedad.Tipo.AVISO,
        texto=data["texto"],
        creado_por=request.user,
    )
    return JsonResponse(_novedad_to_dict(nov), status=201)


@login_required
@require_http_methods(["DELETE"])
def api_novedad_detail(request, pk):
    if not _es_admin(request):
        return HttpResponseForbidden()
    nov = get_object_or_404(Novedad, pk=pk)
    nov.delete()
    return JsonResponse({"ok": True})


# ── Cumpleaños ─────────────────────────────────────────────────────────────

@login_required
@require_http_methods(["GET"])
def api_cumpleanios(request):
    if not _puede_ver(request):
        return HttpResponseForbidden()

    hoy = timezone.localdate()
    items = []
    for emp in Empleado.objects.filter(estado=Empleado.Estado.ACTIVO, fecha_nacimiento__isnull=False):
        proximo = emp.proximo_cumpleanios(hoy)
        dias = (proximo - hoy).days
        if dias == 0:
            badge, badge_label = "pendiente", "Hoy"
        elif dias == 7:
            badge, badge_label = "pendiente", "En 7 días"
        else:
            badge, badge_label = "borrador", "Este año"
        items.append({
            "id": emp.id,
            "nombre_completo": emp.nombre_completo,
            "iniciales": emp.iniciales,
            "fecha": proximo.isoformat(),
            "dias_restantes": dias,
            "badge": badge,
            "badge_label": badge_label,
        })
    items.sort(key=lambda i: i["dias_restantes"])
    return JsonResponse({"cumpleanios": items})