from django import forms
from .models import Client

class UpdatePerfilForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = (
            'username', 'first_name', 'last_name',
            'email', 'phone', 'birthdate', 'cpf'
        )
        widgets = {
            'username': forms.TextInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
            'first_name': forms.TextInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
            'last_name': forms.TextInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
            'email': forms.EmailInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
            'phone': forms.TextInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
            'birthdate': forms.DateInput({'class': 'form-control', 'type': 'date', 'style': 'background-color: var(--realce-color)'}, format='%d/%m/%Y'),
            'cpf': forms.TextInput({'class': 'form-control', 'style': 'background-color: var(--realce-color)'}),
        }
