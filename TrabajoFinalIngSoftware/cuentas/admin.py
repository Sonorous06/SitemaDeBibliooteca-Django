from django.contrib import admin 
from django.contrib.auth.admin import UserAdmin 
from .models import Usuario 

@admin.register(Usuario) 
class UsuarioAdmin(UserAdmin): 
    
    # Agregamos  campos personalizados al formulario del Admin
    fieldsets = UserAdmin.fieldsets + ( ('Información de Biblioteca', { 'fields': ('tipo_usuario', 'telefono', 'bloqueado', 'motivo_bloqueo') }), ) 
    # Columnas que se mostrarán en la tabla principal de usuarios
    list_display = [
        'username', 
        'first_name', 
        'last_name', 
        'tipo_usuario', 
        'bloqueado',
        'is_staff'] 
    # Filtros laterales 
    list_filter = [
        'tipo_usuario', 
        'bloqueado',
        'is_staff']