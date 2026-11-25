from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

from .models import Carrera, Departamento, Estudiante, Profesor


Usuario = get_user_model()


class LectorForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Contraseña",
        required=False,
        widget=forms.PasswordInput(),
        help_text="Al crear una cuenta es obligatoria. "
        "Al editar, déjala vacía para conservar la actual.",
    )

    password2 = forms.CharField(
        label="Confirmar contraseña",
        required=False,
        widget=forms.PasswordInput(),
    )

    matricula = forms.CharField(
        label="Matrícula del estudiante",
        max_length=20,
        required=False,
    )

    carrera = forms.ModelChoiceField(
        label="Carrera del estudiante",
        queryset=Carrera.objects.none(),
        required=False,
    )

    semestre = forms.IntegerField(
        label="Semestre del estudiante",
        min_value=1,
        max_value=12,
        required=False,
    )

    num_empleado = forms.CharField(
        label="Número de empleado del profesor",
        max_length=20,
        required=False,
    )

    departamento = forms.ModelChoiceField(
        label="Departamento del profesor",
        queryset=Departamento.objects.none(),
        required=False,
    )

    class Meta:
        model = Usuario

        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "telefono",
            "tipo_usuario",
        ]

        labels = {
            "username": "Nombre de usuario",
            "first_name": "Nombre",
            "last_name": "Apellidos",
            "email": "Correo electrónico",
            "telefono": "Teléfono",
            "tipo_usuario": "Tipo de lector",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["tipo_usuario"].choices = [
            ("ESTUDIANTE", "Estudiante"),
            ("PROFESOR", "Profesor"),
        ]

        self.fields["email"].required = True
        self.fields["first_name"].required = True
        self.fields["last_name"].required = True

        self.fields["carrera"].queryset = Carrera.objects.order_by("nombre")
        self.fields["departamento"].queryset = (
            Departamento.objects.order_by("nombre")
        )

        if self.instance.pk:
            self.fields["tipo_usuario"].disabled = True

            estudiante = Estudiante.objects.filter(
                usuario_id=self.instance.pk,
            ).first()

            profesor = Profesor.objects.filter(
                usuario_id=self.instance.pk,
            ).first()

            if self.instance.tipo_usuario == "ESTUDIANTE" and estudiante:
                self.initial.update(
                    {
                        "matricula": estudiante.matricula,
                        "carrera": estudiante.carrera_id,
                        "semestre": estudiante.semestre,
                    }
                )

            if self.instance.tipo_usuario == "PROFESOR" and profesor:
                self.initial.update(
                    {
                        "num_empleado": profesor.num_empleado,
                        "departamento": profesor.departamento_id,
                    }
                )
        else:
            self.fields["password1"].required = True
            self.fields["password2"].required = True

        for campo in self.fields.values():
            campo.widget.attrs["class"] = (
                "w-full px-4 py-3 rounded-lg border "
                "border-line bg-cream text-coffee"
            )

    def clean_username(self):
        username = self.cleaned_data["username"]

        if Usuario.objects.filter(
            username__iexact=username,
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                "Ya existe una cuenta con ese nombre de usuario."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if Usuario.objects.filter(
            email__iexact=email,
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(
                "Ese correo ya pertenece a otra cuenta."
            )

        return email

    def clean(self):
        datos = super().clean()

        password1 = datos.get("password1")
        password2 = datos.get("password2")

        if password1 != password2:
            self.add_error(
                "password2",
                "Las contraseñas no coinciden.",
            )

        if password1:
            candidato = Usuario(
                username=datos.get("username", ""),
                first_name=datos.get("first_name", ""),
                last_name=datos.get("last_name", ""),
                email=datos.get("email", ""),
            )

            try:
                validate_password(password1, user=candidato)
            except forms.ValidationError as error:
                self.add_error("password1", error)

        tipo = datos.get("tipo_usuario")

        if tipo == "ESTUDIANTE":
            for campo in ("matricula", "carrera", "semestre"):
                if campo not in self.errors and not datos.get(campo):
                    self.add_error(
                        campo,
                        "Este dato es obligatorio para estudiantes.",
                    )

            matricula = datos.get("matricula")

            if matricula and Estudiante.objects.filter(
                matricula=matricula,
            ).exclude(usuario_id=self.instance.pk).exists():
                self.add_error(
                    "matricula",
                    "Esta matrícula ya está registrada.",
                )

        elif tipo == "PROFESOR":
            for campo in ("num_empleado", "departamento"):
                if campo not in self.errors and not datos.get(campo):
                    self.add_error(
                        campo,
                        "Este dato es obligatorio para profesores.",
                    )

            numero = datos.get("num_empleado")

            if numero and Profesor.objects.filter(
                num_empleado=numero,
            ).exclude(usuario_id=self.instance.pk).exists():
                self.add_error(
                    "num_empleado",
                    "Este número de empleado ya está registrado.",
                )

        return datos


def guardar_lector(form):
    """El llamador debe ejecutar esta función dentro de una transacción."""
    usuario = form.save(commit=False)

    password = form.cleaned_data.get("password1")
    if password:
        usuario.set_password(password)

    usuario.save()

    if usuario.tipo_usuario == "ESTUDIANTE":
        Estudiante.objects.update_or_create(
            usuario=usuario,
            defaults={
                "matricula": form.cleaned_data["matricula"],
                "carrera": form.cleaned_data["carrera"],
                "semestre": form.cleaned_data["semestre"],
            },
        )
    else:
        Profesor.objects.update_or_create(
            usuario=usuario,
            defaults={
                "num_empleado": form.cleaned_data["num_empleado"],
                "departamento": form.cleaned_data["departamento"],
            },
        )

    return usuario