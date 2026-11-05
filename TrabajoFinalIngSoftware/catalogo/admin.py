from django.contrib import admin
from .models import Categoria, Editorial, Autor, Libro, LibroAutor, Ejemplar, SugerenciaAdquisicion

class LibroAutorInline(admin.TabularInline):
    model = Ejemplar
    extra = 1
    
class EjemplarInline(admin.TabularInline): 
    model = Ejemplar 
    extra = 1
    
@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'isbn', 'categoria', 'editorial', 'activo') 
    search_fields = ('titulo', 'isbn') 
    list_filter = ('categoria', 'editorial', 'activo') 
    inlines = [LibroAutorInline, EjemplarInline]

admin.site.register(Categoria) 
admin.site.register(Editorial) 
admin.site.register(Autor) 
admin.site.register(Ejemplar) 
admin.site.register(SugerenciaAdquisicion)