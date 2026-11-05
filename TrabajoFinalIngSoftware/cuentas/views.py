from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

# Create your views here.
@login_required
def home_view(request):
    """Muestra la pagina principal solo si el usuario ha iniciado sesion"""
    return render(request, 'home.html')
    

#MODULO 2 --PRESTAMOS
@login_required
def prestamos_view(request):
    return HttpResponse(""" 
        <h1>Mis presstamos</h1> 
        <p>nahomi</p> 
        <br> 
        <a href="/">Volver al Inicio</a> 
    """)

#MODULO 3 --HISTORIAL Y PENALIZACION
@login_required
def historial_view(request):
    return HttpResponse(""" 
        <h1>Historial y Penalizaciones</h1> 
        <p>nahomi</p> 
        <br> 
        <a href="/">Volver al Inicio</a> 
    """)