from django import forms

from apps.core.models import SystemUser
from apps.entities.models import Entity
from .models import OnboardingTemplate, TemplateEntity, TemplateEntityNotificationRule

WIDGET_CLASSES = 'w-full rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500'


class OnboardingTemplateForm(forms.ModelForm):
    class Meta:
        model = OnboardingTemplate
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'F.eks. "Standard onboarding - IT"',
            }),
            'description': forms.Textarea(attrs={
                'class': WIDGET_CLASSES,
                'rows': 3,
                'placeholder': 'Beskriv hvad denne skabelon dækker...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
            }),
        }


class TemplateEntityForm(forms.ModelForm):
    class Meta:
        model = TemplateEntity
        fields = ['entity', 'days_before_start', 'default_assignee', 'sort_order']
        widgets = {
            'entity': forms.Select(attrs={'class': WIDGET_CLASSES}),
            'days_before_start': forms.NumberInput(attrs={
                'class': WIDGET_CLASSES,
                'placeholder': 'F.eks. 5',
            }),
            'default_assignee': forms.Select(attrs={'class': WIDGET_CLASSES}),
            'sort_order': forms.NumberInput(attrs={
                'class': 'w-24 rounded-lg border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500',
            }),
        }

    def __init__(self, *args, template=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['entity'].queryset = Entity.objects.all()
        self.fields['default_assignee'].queryset = SystemUser.objects.filter(is_active=True)
        self.fields['default_assignee'].required = False
        self._template = template

    def clean_entity(self):
        entity = self.cleaned_data['entity']
        if self._template and not self.instance.pk:
            if TemplateEntity.objects.filter(template=self._template, entity=entity).exists():
                raise forms.ValidationError('Denne enhed er allerede tilføjet til skabelonen.')
        return entity


class TemplateEntityDependencyForm(forms.Form):
    dependencies = forms.ModelMultipleChoiceField(
        queryset=TemplateEntity.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
        }),
        required=False,
        label='Afhængigheder',
    )

    def __init__(self, *args, template_entity=None, **kwargs):
        super().__init__(*args, **kwargs)
        if template_entity:
            self.fields['dependencies'].queryset = (
                TemplateEntity.objects
                .filter(template=template_entity.template)
                .exclude(pk=template_entity.pk)
                .select_related('entity')
            )
            self.fields['dependencies'].initial = template_entity.dependencies.all()


class NotificationRuleForm(forms.ModelForm):
    class Meta:
        model = TemplateEntityNotificationRule
        fields = ['notify_user', 'send_email', 'send_in_app']
        widgets = {
            'notify_user': forms.Select(attrs={'class': WIDGET_CLASSES}),
            'send_email': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
            }),
            'send_in_app': forms.CheckboxInput(attrs={
                'class': 'rounded border-gray-300 text-indigo-600 focus:ring-indigo-500',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['notify_user'].queryset = SystemUser.objects.filter(is_active=True)
