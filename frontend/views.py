from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import requests
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from sistema_pedidos.models import Cliente, TipoCliente, Pedido, ItemPedido, Comunicacion, ComunicacionDestinatario
from lista_precios.models import Variedad, Tamaño, Familia, ListaPrecios, Precio, Producto, ActualizacionPrecios
from lista_precios.services import aplicar_actualizaciones_pendientes
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse, Http404
from django.contrib.staticfiles import finders
from django.utils.text import slugify
import io
import qrcode
from reportlab.pdfgen import canvas as reportlab_canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import cm, mm
from django.shortcuts import render, get_object_or_404
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer



@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)

            serializer = TokenObtainPairSerializer(data={
                'username': username,
                'password': password
            })
            serializer.is_valid(raise_exception=True)
            access_token = serializer.validated_data['access']

            response = redirect('dashboard')
            response.set_cookie('access_token', access_token, httponly=True)
            return response
        else:
            return render(request, 'login.html', {'error': True})
    else:
        return render(request, 'login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required(login_url='login')
def usuarios_view(request):
    if request.user.perfil.rol == 'admin':
        users = User.objects.all()
        return render(request, 'usuarios.html', {'users': users})
    else:
        return redirect('dashboard')


def establecer_password_view(request, uid, token):
    uid_decodificado = force_str(urlsafe_base64_decode(uid))
    user = User.objects.get(pk=uid_decodificado)
    token_generator = PasswordResetTokenGenerator()
    if token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            password2 = request.POST.get('password2')
            if password == password2:
                user.set_password(password)
                user.save()
                return redirect('login')
            else:
                return render(request, 'establecer_password.html', {'error': 'Las contraseñas no coinciden'})
        else:
            return render(request, 'establecer_password.html')
    else:
        return render(request, 'token_invalido.html')


@login_required(login_url='login')
def clientes_view(request):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        clientes = Cliente.objects.select_related('tipo_cliente', 'lista_precios').all().order_by('razon_social')
        tipos_cliente = TipoCliente.objects.all()
        listas_precios = ListaPrecios.objects.all().order_by('nombre')
        return render(request, 'clientes.html', {
            'clientes': clientes,
            'tipos_cliente': tipos_cliente,
            'listas_precios': listas_precios,
        })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def cliente_detalle_view(request, cliente_id=None):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        tipos_cliente = TipoCliente.objects.all()
        listas_precios = ListaPrecios.objects.all().order_by('-fecha')

        if cliente_id is None:
            return render(request, 'cliente_detalle.html', {
                'cliente': None,
                'tipos_cliente': tipos_cliente,
                'listas_precios': listas_precios,
            })
        else:
            cliente = Cliente.objects.get(pk=cliente_id)
            ruta = f'/catalogo/{cliente.token}/'
            magic_link = request.build_absolute_uri(ruta)
            return render(request, 'cliente_detalle.html', {
                'cliente': cliente,
                'tipos_cliente': tipos_cliente,
                'listas_precios': listas_precios,
                'magic_link': magic_link,
            })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def producto_view(request):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        productos = Producto.objects.all().order_by('nombre', 'variedad__nombre', 'tamaño__nombre')
        variedad = Variedad.objects.all()
        tamaño = Tamaño.objects.all()
        familia = Familia.objects.all()

        PALETA_TAMAÑOS = [
            {'bg': '#EAF3DE', 'texto': '#2E6B0A'},
            {'bg': '#FEF3E7', 'texto': '#9B5800'},
            {'bg': '#E6F1FB', 'texto': '#0D4490'},
        ]

        tamaños_vistos = {}
        for p in productos:
            tam = p.tamaño
            if tam.nombre not in tamaños_vistos:
                idx = len(tamaños_vistos)
                tamaños_vistos[tam.nombre] = PALETA_TAMAÑOS[idx % len(PALETA_TAMAÑOS)]
            color = tamaños_vistos[tam.nombre]
            tam.color_bg = color['bg']
            tam.color_texto = color['texto']

        return render(request, 'productos.html', {
            'productos': productos,
            'variedad': variedad,
            'tamaño': tamaño,
            'familia': familia,
        })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def producto_detalle_view(request, producto_id=None):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        clientes = Cliente.objects.filter(activo=True).order_by('razon_social')
        if producto_id is None:
            variedad = Variedad.objects.all()
            tamaño = Tamaño.objects.all()
            familia = Familia.objects.all()
            return render(request, 'producto_detalle.html', {
                'producto': None,
                'variedad': variedad,
                'tamaño': tamaño,
                'familia': familia,
                'clientes': clientes,
            })
        else:
            producto = Producto.objects.get(pk=producto_id)
            variedad = Variedad.objects.all()
            tamaño = Tamaño.objects.all()
            familia = Familia.objects.all()
            return render(request, 'producto_detalle.html', {
                'producto': producto,
                'variedad': variedad,
                'tamaño': tamaño,
                'familia': familia,
                'clientes': clientes,
            })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def lista_precios_view(request):
    if request.user.perfil.rol == 'admin':
        listas = ListaPrecios.objects.all().order_by('-fecha')
        return render(request, 'lista_precios.html', {'listas': listas})
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def lista_precios_detalle_view(request, lista_precios_id=None):
    if request.user.perfil.rol == 'admin':
        if lista_precios_id is None:
            return render(request, 'lista_precios_detalle.html', {
                'lista_precios': None,
            })
        else:
            lista_precios = ListaPrecios.objects.get(pk=lista_precios_id)
            precios = Precio.objects.filter(lista_precio=lista_precios).select_related(
                'producto', 'producto__tamaño'
            ).order_by('producto__nombre')

            PALETA_TAMAÑOS = [
                {'bg': '#EAF3DE', 'color': '#2E6B0A'},
                {'bg': '#FEF3E7', 'color': '#9B5800'},
                {'bg': '#E6F1FB', 'color': '#0D4490'},
                {'bg': '#FFF0EB', 'color': '#8B2800'},
                {'bg': '#F5EEFE', 'color': '#320A6E'},
            ]

            tamaños_vistos = {}
            precios_actuales = []
            for p in precios:
                tamaño_nombre = p.producto.tamaño.nombre
                if tamaño_nombre not in tamaños_vistos:
                    idx = len(tamaños_vistos)
                    tamaños_vistos[tamaño_nombre] = PALETA_TAMAÑOS[idx % len(PALETA_TAMAÑOS)]
                color = tamaños_vistos[tamaño_nombre]
                precios_actuales.append({
                    'producto': p.producto,
                    'precio': p.precio,
                    'tamaño_bg': color['bg'],
                    'tamaño_color': color['color'],
                })

            actualizacion_pendiente = None
            pendiente = ActualizacionPrecios.objects.filter(
                lista_precio=lista_precios, estado='programada'
            ).prefetch_related('items').first()
            if pendiente:
                actualizacion_pendiente = {
                    'id': pendiente.id,
                    'vigente_desde': timezone.localtime(pendiente.vigente_desde),
                    'cantidad_items': pendiente.items.count(),
                }

            return render(request, 'lista_precios_detalle.html', {
                'lista_precios': lista_precios,
                'precios_actuales': precios_actuales,
                'actualizacion_pendiente': actualizacion_pendiente,
            })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def historico_comunicaciones_view(request):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        comunicaciones = Comunicacion.objects.select_related(
            'actualizacion', 'actualizacion__lista_precio'
        ).prefetch_related('destinatarios').order_by('-creada')

        for c in comunicaciones:
            destinatarios = list(c.destinatarios.all())
            c.total_destinatarios = len(destinatarios)
            c.total_leidos = sum(1 for d in destinatarios if d.leida_en)

        return render(request, 'historico_comunicaciones.html', {
            'comunicaciones': comunicaciones,
        })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def historico_comunicacion_detalle_view(request, comunicacion_id):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        comunicacion = get_object_or_404(Comunicacion, pk=comunicacion_id)
        destinatarios = comunicacion.destinatarios.select_related('cliente').order_by(
            'cliente__nombre_comercio', 'cliente__razon_social'
        )
        return render(request, 'historico_comunicaciones_detalle.html', {
            'comunicacion': comunicacion,
            'destinatarios': destinatarios,
        })
    else:
        return redirect('dashboard')


@login_required(login_url='login')
def centro_pedidos_view(request):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        desde = request.GET.get('desde')
        estado = request.GET.get('estado')

        if desde:
            fecha_desde = desde
        else:
            fecha_desde = timezone.now() - timedelta(days=7)

        if estado:
            todos_estados = [estado]
        else:
            todos_estados = ['nuevo', 'en_proceso', 'completado', 'cancelado']

        estados_filtrados = Pedido.objects.filter(
            estado__in=todos_estados,
            fecha__gte=fecha_desde
        ).order_by('-fecha')

        for pedido in estados_filtrados:
            items = pedido.itempedido_set.all()
            pedido.total_unidades = sum(item.cantidad for item in items)
            pedido.total_precio = sum(item.cantidad * item.precio for item in items)
            for item in items:
                item.subtotal = item.cantidad * item.precio
            pedido.items = items

        return render(request, 'centro_pedidos.html', {'estados_filtrados': estados_filtrados})
    else:
        return redirect('dashboard')


def _pdf_lista_precios(lista, precios, vigente_desde=None):
    """Genera el PDF de una lista de precios a partir de los precios recibidos.
    Lo usan el panel (todos los precios de la lista) y el catálogo del cliente.
    Si vigente_desde tiene fecha, el encabezado indica desde cuándo rigen esos precios."""
    agrupado = {}
    for precio in precios:
        familia = precio.producto.familia
        if familia not in agrupado:
            agrupado[familia] = []
        agrupado[familia].append(precio)

    PALETA_FAMILIAS = [
        {'bg': '#FEF3E7', 'texto': '#8B5200', 'borde': '#E8A020'},
        {'bg': '#FFF0EB', 'texto': '#8B2800', 'borde': '#E8521A'},
        {'bg': '#EAF3DE', 'texto': '#234D0A', 'borde': '#5A9E20'},
        {'bg': '#E1F5EE', 'texto': '#0A3D28', 'borde': '#1D9E75'},
        {'bg': '#E6F1FB', 'texto': '#0A2E5C', 'borde': '#3080D0'},
        {'bg': '#F5EEFE', 'texto': '#320A6E', 'borde': '#7F4DD8'},
    ]

    PALETA_TAMAÑOS = [
        {'bg': '#EAF3DE', 'texto': '#2E6B0A'},
        {'bg': '#FEF3E7', 'texto': '#9B5800'},
        {'bg': '#E6F1FB', 'texto': '#0D4490'},
    ]

    tamaños_vistos = {}
    for i, familia in enumerate(agrupado.keys()):
        color = PALETA_FAMILIAS[i % len(PALETA_FAMILIAS)]
        familia.color_bg = color['bg']
        familia.color_texto = color['texto']
        familia.color_borde = color['borde']

        for precio in agrupado[familia]:
            tamaño = precio.producto.tamaño
            if tamaño.nombre not in tamaños_vistos:
                idx = len(tamaños_vistos)
                tamaños_vistos[tamaño.nombre] = PALETA_TAMAÑOS[idx % len(PALETA_TAMAÑOS)]
            color_tam = tamaños_vistos[tamaño.nombre]
            tamaño.color_bg = color_tam['bg']
            tamaño.color_texto = color_tam['texto']

    def formatear_medida(producto):
        if producto.tipo_medida == 'diametro':
            return f'Ø {producto.medida_1} cm'
        elif producto.tipo_medida == 'largo_ancho':
            return f'Largo {producto.medida_1} cm · Ancho {producto.medida_2} cm'
        elif producto.tipo_medida == 'largo_ancho_alto':
            return f'{producto.medida_1} cm · {producto.medida_2} cm · {producto.medida_3} cm'
        return ''

    ficha_tecnica = {}
    for precio in precios:
        producto = precio.producto
        clave = (producto.nombre, producto.tamaño.nombre)
        if clave not in ficha_tecnica:
            ficha_tecnica[clave] = {
                'nombre': f'{producto.nombre} {producto.tamaño.nombre}',
                'dimensiones': formatear_medida(producto),
                'variedades': set(),
            }
        ficha_tecnica[clave]['variedades'].add(producto.variedad.nombre)

    ficha_tecnica_lista = []
    for item in ficha_tecnica.values():
        item['variedades'] = ', '.join(sorted(item['variedades']))
        ficha_tecnica_lista.append(item)

    logo_path = finders.find('img/logo.png')
    logo_url = 'file:///' + logo_path.replace('\\', '/')

    html_string = render_to_string('lista_precios_pdf.html', {
        'agrupado': agrupado,
        'lista': lista,
        'ficha_tecnica': ficha_tecnica_lista,
        'logo_url': logo_url,
        'vigente_desde': vigente_desde,
    })
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="lista_precios_{lista.nombre}.pdf"'
    return response


@login_required(login_url='login')
def lista_precios_pdf_view(request, lista_precios_id):
    lista = ListaPrecios.objects.get(pk=lista_precios_id)
    precios = Precio.objects.filter(lista_precio=lista)
    return _pdf_lista_precios(lista, precios)


def _precios_ultima_lista(lista, cliente):
    """Precios de la última lista de un cliente, para su PDF.
    - Si la lista tiene una actualización programada, se muestran esos precios
      (aunque todavía no estén vigentes). Si no, los vigentes.
    - Solo productos activos y visibles para el cliente: si un producto tiene
      clientes exclusivos y el cliente no es uno de ellos, no aparece
      (misma regla que el catálogo).
    Devuelve (precios, vigente_desde); vigente_desde es None si no hay lista futura."""
    precios = {}
    for precio in Precio.objects.filter(lista_precio=lista).select_related(
        'producto', 'producto__variedad', 'producto__tamaño', 'producto__familia'
    ).prefetch_related('producto__clientes_exclusivos'):
        precios[precio.producto_id] = precio

    programada = ActualizacionPrecios.objects.filter(
        lista_precio=lista, estado='programada'
    ).first()
    vigente_desde = None
    if programada:
        vigente_desde = timezone.localtime(programada.vigente_desde).date()
        items = programada.items.select_related(
            'producto', 'producto__variedad', 'producto__tamaño', 'producto__familia'
        ).prefetch_related('producto__clientes_exclusivos')
        for item in items:
            precio = precios.get(item.producto_id)
            if precio is not None:
                precio.precio = item.precio_nuevo  # solo en memoria, no se guarda
            else:
                precios[item.producto_id] = Precio(
                    lista_precio=lista, producto=item.producto, precio=item.precio_nuevo
                )

    visibles = []
    for precio in precios.values():
        producto = precio.producto
        if not producto.activo:
            continue
        exclusivos = list(producto.clientes_exclusivos.all())
        if exclusivos and cliente not in exclusivos:
            continue
        visibles.append(precio)
    return visibles, vigente_desde


# ---------------------------------------------------------------------------
# Etiqueta QR del magic link (para imprimir y entregar al cliente)
# ---------------------------------------------------------------------------

_QR_ANCHO_ETIQUETA = 8 * cm
_QR_ALTO_ETIQUETA = 10 * cm
_QR_PADDING = 3.5 * mm
_QR_COLOR_TEXTO = (0.15, 0.13, 0.12)
_QR_COLOR_SECUNDARIO = (0.5, 0.48, 0.47)


def _qr_generar_imagen(link):
    qr = qrcode.QRCode(border=1, box_size=10, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(link)
    qr.make(fit=True)
    return qr.make_image(fill_color='black', back_color='white').convert('RGB')


def _qr_envolver_texto(c, texto, fuente, tamaño, ancho_max, max_lineas=2):
    palabras = texto.split(' ')
    lineas, actual = [], ''
    for palabra in palabras:
        prueba = f'{actual} {palabra}'.strip()
        if c.stringWidth(prueba, fuente, tamaño) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)

    if len(lineas) > max_lineas:
        lineas = lineas[:max_lineas]
        ultima = lineas[-1]
        while c.stringWidth(ultima + '...', fuente, tamaño) > ancho_max and len(ultima) > 1:
            ultima = ultima[:-1]
        lineas[-1] = ultima + '...'
    return lineas


def _qr_envolver_link(c, link, fuente, tamaño, ancho_max):
    if c.stringWidth(link, fuente, tamaño) <= ancho_max:
        return [link]
    marcador = '/catalogo/'
    if marcador in link:
        idx = link.index(marcador) + len(marcador)
        linea1, linea2 = link[:idx], link[idx:]
        if (c.stringWidth(linea1, fuente, tamaño) <= ancho_max and
                c.stringWidth(linea2, fuente, tamaño) <= ancho_max):
            return [linea1, linea2]
    return _qr_envolver_texto(c, link, fuente, tamaño, ancho_max, max_lineas=2)


def _qr_generar_pdf_etiqueta(nombre, link):
    """Arma en memoria el PDF de la etiqueta de 8x10cm con el QR del magic
    link, el logo y los datos del cliente. Devuelve los bytes del PDF."""
    logo_path = finders.find('img/logo.png')
    logo_reader = ImageReader(logo_path)
    from PIL import Image as PILImage
    logo_ratio = PILImage.open(logo_path).width / PILImage.open(logo_path).height

    buffer = io.BytesIO()
    c = reportlab_canvas.Canvas(buffer, pagesize=(_QR_ANCHO_ETIQUETA, _QR_ALTO_ETIQUETA))

    centro_x = _QR_ANCHO_ETIQUETA / 2
    inner_ancho = _QR_ANCHO_ETIQUETA - _QR_PADDING * 2

    fuente_cta, tam_cta = 'Helvetica-Bold', 10.5
    fuente_nombre, tam_nombre = 'Helvetica-Bold', 9.5
    fuente_link, tam_link = 'Helvetica', 6.3

    lineas_cta = _qr_envolver_texto(c, 'Escaneá y hacé tu pedido', fuente_cta, tam_cta, inner_ancho, max_lineas=2)
    nombre_mostrado = nombre if len(nombre) <= 60 else nombre[:57] + '...'
    lineas_nombre = _qr_envolver_texto(c, nombre_mostrado, fuente_nombre, tam_nombre, inner_ancho, max_lineas=2)
    lineas_link = _qr_envolver_link(c, link, fuente_link, tam_link, inner_ancho)

    logo_alto = 1.0 * cm
    logo_ancho = logo_alto * logo_ratio
    if logo_ancho > inner_ancho * 0.7:
        logo_ancho = inner_ancho * 0.7
        logo_alto = logo_ancho / logo_ratio

    qr_lado = min(4.7 * cm, inner_ancho)

    interlineado_cta = tam_cta * 1.2
    interlineado_nombre = tam_nombre * 1.25
    interlineado_link = tam_link * 1.3

    gap_logo_cta = 5 * mm
    gap_cta_qr = 4 * mm
    gap_qr_nombre = 5 * mm
    gap_nombre_link = 2 * mm

    alto_contenido = (
        logo_alto + gap_logo_cta +
        len(lineas_cta) * interlineado_cta + gap_cta_qr +
        qr_lado + gap_qr_nombre +
        len(lineas_nombre) * interlineado_nombre + gap_nombre_link +
        len(lineas_link) * interlineado_link
    )

    cursor_y = _QR_ALTO_ETIQUETA / 2 + alto_contenido / 2

    c.drawImage(logo_reader, centro_x - logo_ancho / 2, cursor_y - logo_alto,
                width=logo_ancho, height=logo_alto, mask='auto')
    cursor_y -= logo_alto + gap_logo_cta

    c.setFont(fuente_cta, tam_cta)
    c.setFillColorRGB(*_QR_COLOR_TEXTO)
    for linea in lineas_cta:
        cursor_y -= interlineado_cta
        c.drawCentredString(centro_x, cursor_y + interlineado_cta * 0.22, linea)
    cursor_y -= gap_cta_qr

    qr_img = _qr_generar_imagen(link)
    c.drawImage(ImageReader(qr_img), centro_x - qr_lado / 2, cursor_y - qr_lado,
                width=qr_lado, height=qr_lado)
    cursor_y -= qr_lado + gap_qr_nombre

    c.setFont(fuente_nombre, tam_nombre)
    c.setFillColorRGB(*_QR_COLOR_TEXTO)
    for linea in lineas_nombre:
        cursor_y -= interlineado_nombre
        c.drawCentredString(centro_x, cursor_y + interlineado_nombre * 0.22, linea)
    cursor_y -= gap_nombre_link

    c.setFont(fuente_link, tam_link)
    c.setFillColorRGB(*_QR_COLOR_SECUNDARIO)
    for linea in lineas_link:
        cursor_y -= interlineado_link
        c.drawCentredString(centro_x, cursor_y + interlineado_link * 0.22, linea)

    c.save()
    return buffer.getvalue()


@login_required(login_url='login')
def cliente_qr_etiqueta_view(request, cliente_id):
    if request.user.perfil.rol not in ('admin', 'colab'):
        return redirect('dashboard')

    cliente = get_object_or_404(Cliente, pk=cliente_id)
    if not cliente.token:
        raise Http404('Este cliente todavía no tiene un link generado.')

    link = request.build_absolute_uri(f'/catalogo/{cliente.token}/')
    nombre = cliente.nombre_comercio or cliente.razon_social or cliente.nombre

    pdf_bytes = _qr_generar_pdf_etiqueta(nombre, link)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="qr-{slugify(nombre)}.pdf"'
    return response


def lista_precios_pdf_catalogo_view(request, token):
    cliente = get_object_or_404(Cliente, token=token, activo=True)
    lista = cliente.lista_precios
    if not lista:
        raise Http404('El cliente no tiene una lista de precios asignada.')
    precios, vigente_desde = _precios_ultima_lista(lista, cliente)
    return _pdf_lista_precios(lista, precios, vigente_desde)


def comanda(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id)
    items = pedido.itempedido_set.all()
    return render(request, 'comanda.html', {
        'pedido': pedido,
        'items': items,
    })


def catalogo_view(request, token):
    cliente = get_object_or_404(Cliente, token=token, activo=True)

    lista = cliente.lista_precios
    if lista:
        aplicar_actualizaciones_pendientes(lista)
    if not lista:
        return render(request, 'catalogo.html', {
            'cliente': cliente,
            'productos_con_precio': [],
            'sin_lista': True,
            'metodos': [],
        })

    precios = Precio.objects.filter(lista_precio=lista).select_related(
        'producto', 'producto__variedad', 'producto__tamaño', 'producto__familia'
    ).order_by('producto__familia__nombre', 'producto__nombre', 'producto__tamaño__nombre')

    PALETA_TAMAÑOS = [
        {'bg': '#EAF3DE', 'color': '#2E6B0A'},
        {'bg': '#FEF3E7', 'color': '#9B5800'},
        {'bg': '#E6F1FB', 'color': '#0D4490'},
        {'bg': '#FFF0EB', 'color': '#8B2800'},
        {'bg': '#F5EEFE', 'color': '#320A6E'},
    ]

    tamaños_vistos = {}
    productos_con_precio = []
    for precio in precios:
        p = precio.producto
        if not p.activo:
            continue
        exclusivos = p.clientes_exclusivos.all()
        if exclusivos.exists() and cliente not in exclusivos:
            continue
        tamaño_nombre = p.tamaño.nombre
        if tamaño_nombre not in tamaños_vistos:
            idx = len(tamaños_vistos)
            tamaños_vistos[tamaño_nombre] = PALETA_TAMAÑOS[idx % len(PALETA_TAMAÑOS)]
        color = tamaños_vistos[tamaño_nombre]
        productos_con_precio.append({
            'producto': p,
            'precio': precio.precio,
            'tamaño_bg': color['bg'],
            'tamaño_color': color['color'],
        })

    metodos = []
    if cliente.permite_retiro:
        metodos.append(('retiro', 'Retiro en fábrica'))
    if cliente.permite_domicilio:
        metodos.append(('entrega_domicilio', 'Entrega a domicilio'))

    return render(request, 'catalogo.html', {
        'cliente': cliente,
        'productos_con_precio': productos_con_precio,
        'metodos': metodos,
    })


def perfil_catalogo_view(request, token):
    cliente = get_object_or_404(Cliente, token=token, activo=True)
    pedidos = Pedido.objects.filter(cliente=cliente).order_by('-fecha')
    mostrar_todos = request.GET.get('todos') == '1'
    pedidos_mostrados = list(pedidos if mostrar_todos else pedidos[:10])

    for pedido in pedidos_mostrados:
        items = list(pedido.itempedido_set.all())
        for item in items:
            item.subtotal = item.cantidad * item.precio
        pedido.total_unidades = sum(item.cantidad for item in items)
        pedido.total_precio = sum(item.subtotal for item in items)
        pedido.items = items

    return render(request, 'perfil_catalogo.html', {
        'cliente': cliente,
        'pedidos': pedidos_mostrados,
        'mostrar_todos': mostrar_todos,
        'total_pedidos': pedidos.count(),
    })


@login_required(login_url='login')
def subir_pdf_catalogo_view(request, lista_precios_id):
    if request.user.perfil.rol != 'admin':
        return redirect('dashboard')

    lista = get_object_or_404(ListaPrecios, id=lista_precios_id)

    if request.method == 'POST' and request.FILES.get('pdf_catalogo'):
        lista.pdf_catalogo = request.FILES['pdf_catalogo']
        lista.save()

    return redirect('lista_precios_editar', lista_precios_id=lista_precios_id)

@login_required(login_url='login')
def calculadora_produccion_view(request):
    print("ENTRANDO A CALCULADORA")
    if request.user.perfil.rol not in ['admin', 'colab']:
        return redirect('dashboard')
    print("ROL OK:", request.user.perfil.rol)
    return render(request, 'calculadora_produccion.html')