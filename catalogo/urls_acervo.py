from django.urls import path

from . import views_acervo as views


urlpatterns = [
    path("", views.lista_acervo_view, name="acervo_lista"),
    path(
        "libros/nuevo/", views.formulario_libro_view, name="acervo_crear_libro"
    ),
    path(
        "libros/<int:libro_id>/editar/",
        views.formulario_libro_view,
        name="acervo_editar_libro",
    ),
    path(
        "libros/<int:libro_id>/ejemplares/",
        views.lista_ejemplares_view,
        name="acervo_ejemplares",
    ),
    path(
        "libros/<int:libro_id>/ejemplares/nuevo/",
        views.formulario_ejemplar_view,
        name="acervo_crear_ejemplar",
    ),
    path(
        "ejemplares/<int:ejemplar_id>/editar/",
        views.formulario_ejemplar_view,
        name="acervo_editar_ejemplar",
    ),
    path(
        "datos/<str:tipo>/",
        views.lista_auxiliar_view,
        name="acervo_auxiliares",
    ),
    path(
        "datos/<str:tipo>/nuevo/",
        views.formulario_auxiliar_view,
        name="acervo_crear_auxiliar",
    ),
    path(
        "datos/<str:tipo>/<int:registro_id>/editar/",
        views.formulario_auxiliar_view,
        name="acervo_editar_auxiliar",
    ),
    path(
        "datos/<str:tipo>/<int:registro_id>/eliminar/",
        views.eliminar_auxiliar_view,
        name="acervo_eliminar_auxiliar",
    ),
]
