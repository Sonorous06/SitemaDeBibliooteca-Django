from django import forms
from django.contrib.auth import get_user_model

user = get_user_model()

class RecuperarPasswordCustomForm(forms.Form):
    username = forms.CharField(
        label = "Nombre de usuario o matricula",
        widget= forms.TextInput(attrs={
            'class' : 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-sky-500',
            'placeholder' : 'Ej. profesor01'
        })
    )
    
    corre_destino = forms.EmailField(
        label = 'Correo electronico para recbir el enlace',
        widget=forms.EmailInput(attrs={
            'class' : 'w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-sky-500',
            'placehoder ' : 'tu_correo_@gmail.com'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if not user.objects.filter(username__iexact=username, is_active=True).exists():
            raise forms.ValidationError("No existe ninguna cuenta activa con este usuario/matrícula.")
        return username