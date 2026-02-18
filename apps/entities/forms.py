from django import forms
from django.forms import inlineformset_factory

from .models import Entity, CustomFieldDefinition


class EntityForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ['name', 'description', 'category']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'F.eks. "Bestil laptop"',
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'rows': 3,
                'placeholder': 'Beskriv hvad denne enhed indebærer...',
            }),
            'category': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
                'placeholder': 'F.eks. "IT", "HR", "Adgang"',
            }),
        }


class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomFieldDefinition
        fields = ['name', 'field_type', 'is_required', 'default_value', 'sort_order']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm',
                'placeholder': 'Feltnavn',
            }),
            'field_type': forms.Select(attrs={
                'class': 'rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm',
            }),
            'is_required': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
            }),
            'default_value': forms.TextInput(attrs={
                'class': 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm',
                'placeholder': 'Standardværdi',
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'w-20 rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 text-sm',
            }),
        }


CustomFieldFormSet = inlineformset_factory(
    Entity,
    CustomFieldDefinition,
    form=CustomFieldForm,
    extra=0,
    can_delete=True,
)
