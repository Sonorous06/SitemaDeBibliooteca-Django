import csv
import io

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect, render

from .forms_lectores import LectorForm, guardar_lector
from .models import Carrera, Departamento


COLUMNAS = [
    "username",
    "first_name",
    "last_name",
    "email",
    "telefono",
    "tipo_usuario",
    "password",
    "matricula",
    "carrera",
    "semestre",
    "num_empleado",
    "departamento",
]


class ImportarLectoresForm(forms.Form):
    archivo = forms.FileField(
        label="Archivo CSV",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".csv",
                "class": (
                    "w-full px-4 py-3 border border-line "
                    "rounded-lg bg-cream text-coffee"
                ),
            }
        ),
    )

    def clean_archivo(self):
        archivo = self.cleaned_data["archivo"]

        if not archivo.name.lower().endswith(".csv"):
            raise forms.ValidationError("Selecciona un archivo .csv.")

        if archivo.size > 1024 * 1024:
            raise forms.ValidationError(
                "El archivo no puede superar 1 MB."
            )

        try:
            texto = archivo.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            raise forms.ValidationError(
                "Guarda el archivo con codificación UTF-8."
            )

        filas = []

        try:
            muestra = texto[:4096]

            try:
                dialecto = csv.Sniffer().sniff(
                    muestra,
                    delimiters=",;",
                )
            except csv.Error:
                dialecto = csv.excel

            lector = csv.reader(
                io.StringIO(texto, newline=""),
                dialect=dialecto,
                strict=True,
            )

            encabezado = next(lector, None)

            if encabezado is None:
                raise forms.ValidationError("El archivo está vacío.")

            encabezado = [columna.strip() for columna in encabezado]

            if (
                len(encabezado) != len(COLUMNAS)
                or set(encabezado) != set(COLUMNAS)
            ):
                raise forms.ValidationError(
                    "El encabezado debe contener exactamente las "
                    "12 columnas indicadas, sin columnas duplicadas."
                )

            for numero, valores in enumerate(lector, start=2):
                if not any(valor.strip() for valor in valores):
                    continue

                if len(valores) != len(encabezado):
                    raise forms.ValidationError(
                        f"Registro {numero}: cantidad de columnas incorrecta."
                    )

                fila = dict(zip(encabezado, valores))

                # Conservar la contraseña tal como fue escrita.
                fila = {
                    clave: valor if clave == "password" else valor.strip()
                    for clave, valor in fila.items()
                }

                filas.append((numero, fila))

                if len(filas) > 500:
                    raise forms.ValidationError(
                        "Se permiten como máximo 500 lectores por archivo."
                    )

        except csv.Error:
            raise forms.ValidationError(
                "El CSV está mal formado. Revisa comillas y separadores."
            )

        if not filas:
            raise forms.ValidationError(
                "El archivo no contiene lectores para importar."
            )

        self.filas = filas
        return archivo


class ErrorImportacion(Exception):
    def __init__(self, errores):
        self.errores = errores


@login_required
def importar_lectores_view(request):
    if request.user.tipo_usuario != "BIBLIOTECARIO":
        messages.error(request, "Acceso exclusivo para el bibliotecario.")
        return redirect("home")

    if request.method not in ("GET", "POST"):
        return HttpResponseNotAllowed(["GET", "POST"])

    form = ImportarLectoresForm(
        data=request.POST if request.method == "POST" else None,
        files=request.FILES if request.method == "POST" else None,
    )

    errores = []

    if request.method == "POST" and form.is_valid():
        carreras = dict(
            Carrera.objects.values_list("clave", "pk")
        )
        departamentos = dict(
            Departamento.objects.values_list("nombre", "pk")
        )

        creados = 0

        try:
            with transaction.atomic():
                for numero, fila in form.filas:
                    datos = {
                        "username": fila["username"],
                        "first_name": fila["first_name"],
                        "last_name": fila["last_name"],
                        "email": fila["email"],
                        "telefono": fila["telefono"],
                        "tipo_usuario": fila["tipo_usuario"].upper(),
                        "password1": fila["password"],
                        "password2": fila["password"],
                        "matricula": fila["matricula"],
                        "carrera": carreras.get(fila["carrera"], ""),
                        "semestre": fila["semestre"],
                        "num_empleado": fila["num_empleado"],
                        "departamento": departamentos.get(
                            fila["departamento"],
                            "",
                        ),
                    }

                    lector_form = LectorForm(data=datos)
                    lector_form.is_valid()

                    if (
                        datos["tipo_usuario"] == "ESTUDIANTE"
                        and fila["carrera"]
                        and fila["carrera"] not in carreras
                    ):
                        lector_form.add_error(
                            "carrera",
                            "La clave de carrera no existe.",
                        )

                    if (
                        datos["tipo_usuario"] == "PROFESOR"
                        and fila["departamento"]
                        and fila["departamento"] not in departamentos
                    ):
                        lector_form.add_error(
                            "departamento",
                            "El departamento no existe.",
                        )

                    if lector_form.errors:
                        for campo, mensajes in lector_form.errors.items():
                            etiqueta = (
                                lector_form.fields[campo].label
                                if campo in lector_form.fields
                                else "Datos generales"
                            )

                            for mensaje in mensajes:
                                errores.append(
                                    f"Registro {numero} — "
                                    f"{etiqueta}: {mensaje}"
                                )
                    else:
                        guardar_lector(lector_form)
                        creados += 1

                    if len(errores) >= 20:
                        errores.append(
                            "Se muestran los primeros errores. "
                            "Corrige el archivo y vuelve a importarlo."
                        )
                        break

                if errores:
                    # Revertir también las filas que eran válidas.
                    raise ErrorImportacion(errores)

        except ErrorImportacion as error:
            errores = error.errores

        except IntegrityError:
            errores = [
                "No se importó ninguna cuenta porque un dato único "
                "entró en conflicto con otro registro. Revisa usuario, "
                "correo, matrícula y número de empleado."
            ]

        else:
            messages.success(
                request,
                f"Importación completada: {creados} lectores creados.",
            )
            return redirect("lista_usuarios")

    return render(
        request,
        "cuentas/importar_lectores.html",
        {
            "form": form,
            "errores": errores,
        },
    )