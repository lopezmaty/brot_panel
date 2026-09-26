"""Vínculo entre el empleado del reloj (Control Horario) y su legajo (módulo Legajos).

El reloj trae nombres como "Brito Tomas Alberto" y el legajo guarda nombre y
apellido por separado, así que se vincula por coincidencia de palabras: todo el
apellido tiene que aparecer y al menos uno de los nombres.
"""
import re
import unicodedata


def _tokens(*textos):
    salida = set()
    for t in textos:
        t = unicodedata.normalize('NFD', t or '').encode('ascii', 'ignore').decode().lower()
        salida |= {p for p in re.split(r'[^a-z]+', t) if len(p) > 1}
    return salida


def coincide(emp_reloj, legajo):
    palabras = _tokens(emp_reloj.nombre, emp_reloj.alias, emp_reloj.nombre_reloj)
    apellido = _tokens(legajo.apellido)
    nombres = _tokens(legajo.nombre)
    return bool(apellido) and apellido <= palabras and bool(nombres & palabras)


def vincular_automaticamente(EmpleadoReloj=None, Legajo=None):
    """Vincula a los empleados del reloj sin legajo con el único legajo que coincide.
    Devuelve la cantidad de vínculos creados. Nunca pisa un vínculo existente."""
    if EmpleadoReloj is None:
        from .models import Empleado as EmpleadoReloj
    if Legajo is None:
        from legajos.models import Empleado as Legajo

    ocupados = set(EmpleadoReloj.objects.exclude(legajo__isnull=True).values_list('legajo_id', flat=True))
    legajos = [l for l in Legajo.objects.all() if l.id not in ocupados]
    creados = 0
    for emp in EmpleadoReloj.objects.filter(legajo__isnull=True):
        candidatos = [l for l in legajos if coincide(emp, l)]
        if len(candidatos) == 1:
            emp.legajo_id = candidatos[0].id
            emp.save(update_fields=['legajo'])
            legajos.remove(candidatos[0])
            creados += 1
    return creados


def datos_legajo(emp):
    """Nombre, DNI y puesto para formularios: primero del legajo, si no del reloj."""
    leg = getattr(emp, 'legajo', None)
    if leg:
        return {
            'legajo_id': leg.id,
            'nombre_completo': f'{leg.nombre} {leg.apellido}'.strip(),
            'dni': leg.dni or emp.dni,
            'puesto': emp.sector_turno or leg.puesto,
            'desde_legajo': True,
        }
    return {
        'legajo_id': None,
        'nombre_completo': emp.nombre_display(),
        'dni': emp.dni,
        'puesto': emp.sector_turno,
        'desde_legajo': False,
    }
