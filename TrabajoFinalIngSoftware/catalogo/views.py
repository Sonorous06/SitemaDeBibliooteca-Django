from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .models import Libro, Categoria

#decorador para solo aquel registrado pueda verlo
@login_required
def catalogo_view(request): #request tiene toda la info del navegador
    """
    Vista principal de catalogos 
    obtiene los libros activos y permite realizar busquedas por titulo y filtrar por categorias
    """
    query = request.GET.get('q','') #?=python , query lo guarda como python
    categoria_id = request.GET.get('categoria','')
    
    #filtro de libros activos en sistema
    libros = Libro.objects.filter(activo=True)
    
    if query:
        libros = libros.filter(
            Q(titulo__icontains=query) | 
            Q(isbn__icontains=query)
        )
    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)
          
    #Consulta a la base de datos
    categorias = Categoria.objects.all()
    
    context = {
        'libros': libros,
        'categorias' : categorias,
        'query': query,
        'categoria_id' : categoria_id  
    }
    
    return render(request, 'catalogo/catalogo.html', context)