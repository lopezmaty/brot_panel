from .models import Notificacion


def notificar(titulo, mensaje='', url='', icono='ti-bell', nivel='info', modulo='', usuario=None, rol=''):
    """Crea una notificación para la campanita del panel.

    Ejemplos:
        notificar('Nuevo pedido #0123', 'Burger Lab · $ 145.000',
                  url='/pedidos/', icono='ti-clipboard-list', modulo='pedidos')
        notificar('Venció el apto médico de Juan', icono='ti-file-alert',
                  nivel='alerta', rol='admin')
        notificar('Tu cierre de caja quedó guardado', usuario=request.user, nivel='exito')
    """
    return Notificacion.objects.create(
        titulo=titulo[:120],
        mensaje=(mensaje or '')[:300],
        url=url or '',
        icono=icono or 'ti-bell',
        nivel=nivel,
        modulo=modulo or '',
        usuario=usuario,
        rol=rol or '',
    )
