from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
import requests
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from sistema_pedidos.models import Cliente, TipoCliente, Producto
from lista_precios.models import Variedad, Tamaño, Familia

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')

@login_required(login_url='login')
def lista_precios_view(request):
    return render(request, 'lista_precios.html')

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
            respuesta = requests.post('http://localhost:8000/api/token/', data={
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
        if cliente_id is None:
            tipos_cliente = TipoCliente.objects.all()
            return render(request, 'cliente_detalle.html', {'cliente': None, 'tipos_cliente': tipos_cliente})

        else:
            cliente = Cliente.objects.get(pk=cliente_id)
            tipos_cliente = TipoCliente.objects.all()
            return render(request, 'cliente_detalle.html', {'cliente': cliente, 'tipos_cliente': tipos_cliente})
    else:
        response = redirect('dashboard')
        return response

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