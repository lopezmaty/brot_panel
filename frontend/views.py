from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import requests
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from sistema_pedidos.models import Cliente, TipoCliente, Producto, ItemPedido, Pedido
from lista_precios.models import Variedad, Tamaño, Familia, ListaPrecios, Precio
from django.utils import timezone
from datetime import timedelta
from django.template.loader import render_to_string
from weasyprint import HTML
from django.http import HttpResponse
from django.contrib.staticfiles import finders

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')

@login_required(login_url='login')
def centro_pedidos_view(request):
    return render(request, 'centro_pedidos.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            url_token = request.build_absolute_uri('/api/token/')
            respuesta = requests.post(url_token, data={
                'username': username,
                'password': password
            })
            datos = respuesta.json()
            access_token = datos['access']
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
    if request.user.perfil.rol  == 'admin':
        users = User.objects.all()
        response = render(request, 'usuarios.html', {'users': users})
        return response
    else:
        response = redirect('dashboard')
        return response
    
def establecer_password_view(request, uid, token):
    uid_decodificado = force_str(urlsafe_base64_decode(uid))
    user = User.objects.get(pk=uid_decodificado)
    token_generator = PasswordResetTokenGenerator()
    if token_generator.check_token(user, token):
        if request.method == 'POST':
            password = request.POST.get('password')
            password2= request.POST.get('password2')
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
        clientes = Cliente.objects.all().order_by('razon_social')
        tipos_cliente = TipoCliente.objects.all()
        response = render(request, 'clientes.html', {'clientes': clientes, 'tipos_cliente': tipos_cliente})
        return response
    else:
        response = redirect('dashboard')
        return response
    
@login_required(login_url='login')
def cliente_detalle_view(request, cliente_id=None):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        tipos_cliente = TipoCliente.objects.all()

        listas_vigentes = []
        categorias = TipoCliente.objects.all()
        for categoria in categorias:
            lista = ListaPrecios.objects.filter(tipo_cliente=categoria).order_by('-fecha').first()
            if lista is not None:
                listas_vigentes.append(lista)

        if cliente_id is None:
            return render(request, 'cliente_detalle.html', {'cliente': None, 'tipos_cliente': tipos_cliente, 'listas_vigentes': listas_vigentes})
        else:
            cliente = Cliente.objects.get(pk=cliente_id)
            ruta = f'/catalogo/{cliente.token}/'
            magic_link = request.build_absolute_uri(ruta)
            return render(request, 'cliente_detalle.html', {'cliente': cliente, 'tipos_cliente': tipos_cliente, 'listas_vigentes': listas_vigentes, 'magic_link': magic_link})
    else:
        return redirect('dashboard')

@login_required(login_url='login')
def producto_view(request):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        productos = Producto.objects.all().order_by('nombre')
        variedad = Variedad.objects.all()
        tamaño = Tamaño.objects.all()
        familia = Familia.objects.all()
        response = render(request, 'productos.html', {'productos': productos, 'variedad': variedad, 'tamaño': tamaño, 'familia': familia})
        return response
    else:
        response = redirect('dashboard')
        return response

@login_required(login_url='login')
def producto_detalle_view(request, producto_id=None):
    if request.user.perfil.rol == 'admin' or request.user.perfil.rol == 'colab':
        if producto_id is None:
            variedad = Variedad.objects.all()
            tamaño = Tamaño.objects.all()
            familia = Familia.objects.all()
            return render(request, 'producto_detalle.html', {'producto': None, 'variedad': variedad, 'tamaño': tamaño, 'familia': familia})

        else:
            producto = Producto.objects.get(pk=producto_id)
            variedad = Variedad.objects.all()
            tamaño = Tamaño.objects.all()
            familia = Familia.objects.all()
            return render(request, 'producto_detalle.html', {'producto': producto, 'variedad': variedad, 'tamaño': tamaño, 'familia': familia})
    else:
        response = redirect('dashboard')
        return response


@login_required(login_url='login')
def lista_precios_view(request):
    if request.user.perfil.rol == 'admin':
        listas_vigentes = []
        categorias = TipoCliente.objects.all()
        for categoria in categorias:
            lista = ListaPrecios.objects.filter(tipo_cliente=categoria).order_by('-fecha').first()
            if lista is not None:
                listas_vigentes.append(lista)
        response = render(request, 'lista_precios.html', {'listas_vigentes': listas_vigentes})
        return response
    else:
        response = redirect('dashboard')
        return response

@login_required(login_url='login')
def lista_precios_detalle_view(request, lista_precios_id=None):
    if request.user.perfil.rol == 'admin':
        categorias = TipoCliente.objects.all()
        if lista_precios_id is None:
            producto = Producto.objects.all()
            response = render(request, 'lista_precios_detalle.html', {'lista_precios': None, 'producto': producto, 'categorias': categorias})
            return response

        else:
            producto = Producto.objects.all()
            lista_precios = ListaPrecios.objects.get(pk=lista_precios_id)
            precios = Precio.objects.filter(lista_precio=lista_precios)

            precios_por_producto = {}
            for precio in precios:
                precios_por_producto[precio.producto.id] = precio.precio

            response = render(request, 'lista_precios_detalle.html', {'lista_precios': lista_precios, 'producto': producto, 'precios_por_producto': precios_por_producto, 'categorias': categorias})
            return response
    else:
        response = redirect('dashboard')
        return response

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
            todos_estados = estado

        else:
            todos_estados = ['nuevo', 'en_proceso']

        estados_filtrados = Pedido.objects.filter(estado__in=todos_estados, fecha__gte=fecha_desde).order_by('-fecha')

        for pedido in estados_filtrados:
            items = pedido.itempedido_set.all()

            pedido.total_unidades = sum(item.cantidad for item in items)
            pedido.total_precio = sum(item.cantidad * item.precio for item in items)

            for item in items:
                item.subtotal = item.cantidad * item.precio

            pedido.items = items

        response = render(request, 'centro_pedidos.html', {'estados_filtrados': estados_filtrados})
        return response

    else:
            response = redirect('dashboard')
            return response

@login_required(login_url='login')
def lista_precios_pdf_view(request, lista_precios_id):
    lista = ListaPrecios.objects.get(pk=lista_precios_id)
    precios = Precio.objects.filter(lista_precio=lista)

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
    })
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="lista_precios_{lista.nombre}.pdf"'
    return response