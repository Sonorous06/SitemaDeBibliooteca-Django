from django.shortcuts import render , redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from .models import Libro, Categoria, SugerenciaAdquisicion
from cuentas.models import Profesor, Departamento

#con este decorador solo los usarios registrados pueded acceder
@login_required
#VISTA CATALOGO PRINCIPAL
def catalogo_view(request):
    """ Vista principal de catálogo: obtiene los libros activos y permite realizar búsquedas por título/ISBN y filtrar por categorías. """
    
    query = request.GET.get('q','').strip() #strip hace que evite que un espacio en blanco antes o despues rompa la busqueda
    categoria_id = request.GET.get('categoria','')
    
    #filtro de libros activos
    libros = Libro.objects.filter(activo=True)
    
    #busqueda multi-campo (RF - 02 !!!!!!!!!)
    if query:
        libros = libros.filter(
            Q(titulo__icontains=query) |
            Q(isbn__icontains=query) |
            Q(autores__nombre__icontains=query) |
            Q(autores__apellidos__icontains=query) |
            Q(editorial__nombre__icontains=query)
        ).distinct() #se usa sobre una coleccion para recuperar una lista con valores unicos (ingora dublucados)
    
    if categoria_id:
        libros = libros.filter(categoria_id=categoria_id)
        
    #consulta de categorias a al base de datos
    categorias = Categoria.objects.all()
    
    context = { 
               'libros': libros, 
               'categorias': categorias, 
               'query': query,
               'categoria_id': categoria_id 
    } 
    return render(request, 'catalogo/catalogo.html',context)

#VISTA PARA QUE EL PROFESOR PUEDA HACE UNA SUGERENCIA  (CU - 16)
@login_required
def sugerir_adquisicion_view(request):
    """ Permite a los docentes solicitar la adquisición de libros que no se encuentran en el catálogo actual. """
    
    #validar que unicamente se pueda acceder como profesor
    if request.user.tipo_usuario != 'PROFESOR':
        messages.error(request, "Solo profesores pueden enviar sugerencias")
        return redirect('catalogo')
    
    if request.method == 'POST':
        titulo = request.POST.get('titulo')
        autores = request.POST.get('autores')
        isbn = request.POST.get('isbn','')
        justificacion = request.POST.get('justificacion')
        
        # Obtener o crear departamento por defecto para evitar errores si no se ha configurado en Admin 
        depto, _ = Departamento.objects.get_or_create(nombre="General")
        
        #Obtener o crear automáticamente el perfil de Profesor asociado al Usuario
        profesor_perfil, _ = Profesor.objects.get_or_create(
            usuario=request.user,
            defaults={
                'num_empleado': f"EMP-{request.user.id}", 
                'departamento': depto 
            } 
        )
        
        SugerenciaAdquisicion.objects.create(
            profesor=request.user,
            titulo=titulo,                
            autores=autores,
            isbn=isbn,
            justificacion=justificacion,
            estado='PENDIENTE'
            )
        messages.success(request, "¡Tu sugerencia de libro ha sido enviada con éxito al bibliotecario!")
        
        return redirect('catalogo')
    
    return render(request,'catalogo/sugerir_adquisicion.html')
            
#VISTA PARA QUE EL BIBLIOTECARIO VEA LAS SUGERENCIAS (cu - 33)
@login_required
def lista_sugerencias_view(request):
    """ Muestra todas las sugerencias al Bibliotecario. """
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acesso exlcusivo para el bibliotecario')
        return redirect('catalogo')
    
    sugerencias = SugerenciaAdquisicion.objects.all().order_by('-fecha')
    return render(request, 'catalogo/lista_sugerencias.html', {'sugerencias' : sugerencias})

#VISTA PARA APROBAR O RECHAZAR SUGE
@login_required
def cambiar_estado_sugerencia(request, sugerencia_id, nuevo_estado):
    """ Cambia el estado de la sugerencia a APROBADA o RECHAZADA. """
    
    #valida acceso solo al bibliotecario
    if request.user.tipo_usuario != 'BIBLIOTECARIO':
        messages.error(request, 'Acceso no autorizado') 
        return redirect('catalogo')
    
    #valida estados permititos
    if nuevo_estado not in ['APROBADA', 'RECHAZADA']:
        messages.error(request, 'Estado no válido')
        return redirect('lista_sugerencias')
    
    #obtener y actualizar la sugerencia
    sugerencia = get_object_or_404(SugerenciaAdquisicion, id=sugerencia_id)
    sugerencia.estado = nuevo_estado
    sugerencia.save()
    
    if nuevo_estado == 'APROBADA':
        messages.success(request, f"La sugerencia '{sugerencia.titulo}' ha sido APROBADA.")
    else:
        messages.info(request, f"La sugerencia '{sugerencia.titulo}' ha sido RECHAZADA.")
        
    return redirect('lista_sugerencias')