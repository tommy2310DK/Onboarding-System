from django import forms
from django.forms import inlineformset_factory

from .models import Category, Entity, CustomFieldDefinition

WIDGET_CLASSES = 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'


class EntityForm(forms.ModelForm):
    class Meta:
        model = Entity
        fields = ['name', 'description', 'category']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'F.eks. "Bestil laptop"',
            }),
            'description': forms.Textarea(attrs={
                'class': WIDGET_CLASSES,
                'rows': 3,
                'placeholder': 'Beskriv hvad denne enhed indebærer...',
            }),
            'category': forms.Select(attrs={
                'class': WIDGET_CLASSES,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all()
        self.fields['category'].empty_label = '-- Ingen kategori --'
        self.fields['category'].required = False


class CustomFieldForm(forms.ModelForm):
    class Meta:
        model = CustomFieldDefinition
        fields = ['name', 'field_type', 'is_required', 'show_on_overview', 'default_value', 'sort_order']
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
            'show_on_overview': forms.CheckboxInput(attrs={
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
