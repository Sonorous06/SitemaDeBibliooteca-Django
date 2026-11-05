from django.db import models
from django.conf import settings

# categoria tematica
class Categoria(models.Model):
    nombre = models.CharField(max_length=100,unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'categoria'
        verbose_name_plural =  'Categorias'
        
    def __str__(self):
        return self.nombre
    
# editorial
class Editorial(models.Model):
    nombre = models.CharField(max_length=150,unique=True)
    pais = models.CharField(max_length=60, blank=True, null=True)
    
    class Meta:
        db_table = 'editorial'
        verbose_name_plural =  'Editoriales'
        
    def __str__(self):
        return self.nombre
        
#autor
class Autor(models.Model):
    nombre = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=150)
    nacionalidad  = models.CharField(max_length=60, blank=True, null=True)
    
    class Meta:
            db_table = 'autor'
            verbose_name_plural =  'Autores'
            
    def __str__(self):
        return self.nombre
    
#libro / titulo
class Libro(models.Model):
    isbn = models.CharField(max_length=13, unique=True) 
    titulo = models.CharField(max_length=255) 
    subtitulo = models.CharField(max_length=255, blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT)
    editorial = models.ForeignKey(Editorial, on_delete=models.PROTECT) 
    autores = models.ManyToManyField(Autor, through='LibroAutor') 
    anio_publicacion = models.PositiveSmallIntegerField(blank=True, null=True) 
    edicion = models.CharField(max_length=30, blank=True, null=True) 
    idioma = models.CharField(max_length=30, default='Español') 
    num_paginas = models.PositiveSmallIntegerField(blank=True, null=True) 
    descripcion = models.TextField(blank=True, null=True) 
    portada = models.ImageField(upload_to='portadas/', blank=True, null=True) 
    costo_reposicion = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) 
    activo = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'libro'
    
    def __str__(self):
        return self.titulo
    
#libro-autor (tabla intermedia) 
class LibroAutor(models.Model):
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE)
    autor = models.ForeignKey(Autor, on_delete=models.PROTECT)
    orden = models.PositiveSmallIntegerField(default=1)
    
    class Meta:
        db_table = 'libro_autor'
        unique_together = ('libro','autor')

#Ejemplar (copia fisica en el estante)
class Ejemplar(models.Model):
    ESTADOS = [
        ('DISPONIBLE', 'Disponible'), 
        ('RESERVADO', 'Reservado'), 
        ('PRESTADO', 'Prestado'), 
        ('EN_REPARACION', 'En reparación'), 
        ('PERDIDO', 'Perdido'), 
        ('BAJA', 'Baja'),
    ]
    
    libro = models.ForeignKey(Libro, on_delete=models.PROTECT, related_name='ejemplares')
    codigo_inventario = models.CharField(max_length=30, unique=True)
    ubicacion = models.CharField(max_length=50, blank=True, null=True) 
    estado = models.CharField(max_length=15, choices=ESTADOS, default='DISPONIBLE') 
    fecha_adquisicion = models.DateField(blank=True, null=True) 
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        db_table = 'ejemplar'
    
    def __str__(self):
        return f"{self.libro.titulo} ({self.codigo_inventario}) - {self.estado}"
    
#Sugerencia de adquisicion (solo para profes)
class SugerenciaAdquisicion(models.Model):
    ESTADOS = [
        ('PENDIENTES', 'Pendiente'),
        ('APROVADA', 'Aprovada'),
        ('RECHAZADA', 'Rechazada'),
    ]
    
    profesor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=255)
    autores = models.CharField(max_length=255)
    isbn = models.CharField(max_length=13, blank=True, null=True)
    justificacion = models.TextField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='PENDIENTE') 
    respuesta = models.CharField(max_length=255, blank=True, null=True) 
    fecha = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sugerencia_adquisicion'
        
    def __str__(self):
        return f"Sugerencia: {self.titulo} - {self.profesor.username}" 