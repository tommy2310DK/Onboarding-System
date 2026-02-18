from django import forms

from apps.core.models import SystemUser
from apps.templates_mgmt.models import OnboardingTemplate

WIDGET_CLASSES = 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'


class OnboardingCreateForm(forms.Form):
    template = forms.ModelChoiceField(
        queryset=OnboardingTemplate.objects.filter(is_active=True),
        label='Skabelon',
        widget=forms.Select(attrs={'class': WIDGET_CLASSES}),
    )
    new_employee_name = forms.CharField(
        max_length=300, label='Navn på ny medarbejder',
        widget=forms.TextInput(attrs={'class': WIDGET_CLASSES, 'placeholder': 'Fulde navn'}),
    )
    new_employee_email = forms.EmailField(
        required=False, label='Email',
        widget=forms.EmailInput(attrs={'class': WIDGET_CLASSES, 'placeholder': 'email@kentaur.dk'}),
    )
    new_employee_department = forms.CharField(
        max_length=200, required=False, label='Afdeling',
        widget=forms.TextInput(attrs={'class': WIDGET_CLASSES, 'placeholder': 'F.eks. IT, HR'}),
    )
    new_employee_position = forms.CharField(
        max_length=300, required=False, label='Stilling',
        widget=forms.TextInput(attrs={'class': WIDGET_CLASSES, 'placeholder': 'F.eks. Udvikler'}),
    )
    start_date = forms.DateField(
        label='Startdato',
        widget=forms.DateInput(attrs={
            'class': WIDGET_CLASSES, 'type': 'date',
        }),
    )
    notes = forms.CharField(
        required=False, label='Noter',
        widget=forms.Textarea(attrs={'class': WIDGET_CLASSES, 'rows': 3}),
    )


class TaskEditForm(forms.Form):
    assignee = forms.ModelChoiceField(
        queryset=SystemUser.objects.filter(is_active=True),
        required=False, label='Ansvarlig',
        widget=forms.Select(attrs={'class': WIDGET_CLASSES}),
    )
    deadline = forms.DateField(
        required=False, label='Deadline',
        widget=forms.DateInput(attrs={'class': WIDGET_CLASSES, 'type': 'date'}),
    )
