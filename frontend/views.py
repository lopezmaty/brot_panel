from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import requests

@login_required(login_url='login')
def dashboard_view(request):
    return render(request, 'dashboard.html')

@login_required(login_url='login')
def lista_precios_view(request):
    return render(request, 'lista_precios.html')

@login_required(login_url='login')
def clientes_view(request):
    return render(request, 'clientes.html')

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