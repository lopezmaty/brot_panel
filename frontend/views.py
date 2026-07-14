from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required

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
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': True})
    else:
        return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')