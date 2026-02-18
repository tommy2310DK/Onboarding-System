from django import forms

from .models import SystemUser

WIDGET_CLASSES = 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'


class SystemUserForm(forms.ModelForm):
    class Meta:
        model = SystemUser
        fields = ['name', 'email', 'department', 'title', 'phone', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'Fulde navn',
            }),
            'email': forms.EmailInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'bruger@kentaur.dk',
            }),
            'department': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'F.eks. IT, HR, Salg',
            }),
            'title': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'F.eks. Udvikler, Konsulent',
            }),
            'phone': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': '+45 12 34 56 78',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
            }),
        }
