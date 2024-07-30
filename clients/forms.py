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
            'username': forms.TextInput({'class': 'form-control'}),
            'first_name': forms.TextInput({'class': 'form-control'}),
            'last_name': forms.TextInput({'class': 'form-control'}),
            'email': forms.EmailInput({'class': 'form-control'}),
            'phone': forms.TextInput({'class': 'form-control'}),
            'birthdate': forms.DateInput({'class': 'form-control', 'type': 'date'}, format='%d/%m/%Y'),
            'cpf': forms.TextInput({'class': 'form-control'}),
        }
