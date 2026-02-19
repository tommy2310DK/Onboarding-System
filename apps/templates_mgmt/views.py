import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.http import require_POST

from .forms import (
    NotificationRuleForm, OnboardingTemplateForm,
    TemplateEntityDependencyForm, TemplateEntityForm,
)
from .models import OnboardingTemplate, TemplateEntity, TemplateEntityNotificationRule
from .services import duplicate_template, validate_dependencies


class TemplateListView(View):
    def get(self, request):
        templates = OnboardingTemplate.objects.prefetch_related('template_entities').all()
        return render(request, 'templates_mgmt/template_list.html', {
            'templates': templates,
        })


class TemplateCreateView(View):
    def get(self, request):
        form = OnboardingTemplateForm()
        return render(request, 'templates_mgmt/template_form.html', {
            'form': form,
            'is_create': True,
        })

    def post(self, request):
        form = OnboardingTemplateForm(request.POST)
        if form.is_valid():
            template = form.save()
            messages.success(request, f'Skabelonen "{template.name}" er oprettet.')
            return redirect('templates_mgmt:detail', pk=template.pk)
        return render(request, 'templates_mgmt/template_form.html', {
            'form': form,
            'is_create': True,
        })


class TemplateDetailView(View):
    def get(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        template_entities = (
            template.template_entities
            .select_related('entity', 'default_assignee')
            .prefetch_related('dependencies__entity', 'notification_rules__notify_user')
        )
        return render(request, 'templates_mgmt/template_detail.html', {
            'template': template,
            'template_entities': template_entities,
        })


class TemplateUpdateView(View):
    def get(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        form = OnboardingTemplateForm(instance=template)
        return render(request, 'templates_mgmt/template_form.html', {
            'form': form,
            'template': template,
            'is_create': False,
        })

    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        form = OnboardingTemplateForm(request.POST, instance=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Skabelonen "{template.name}" er opdateret.')
            return redirect('templates_mgmt:detail', pk=template.pk)
        return render(request, 'templates_mgmt/template_form.html', {
            'form': form,
            'template': template,
            'is_create': False,
        })


class TemplateDeleteView(View):
    def get(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        return render(request, 'templates_mgmt/template_confirm_delete.html', {
            'template': template,
        })

    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        name = template.name
        template.delete()
        messages.success(request, f'Skabelonen "{name}" er slettet.')
        return redirect('templates_mgmt:list')


class AddEntityToTemplateView(View):
    def get(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        form = TemplateEntityForm(template=template)
        return render(request, 'templates_mgmt/template_entity_add.html', {
            'template': template,
            'form': form,
        })

    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        form = TemplateEntityForm(request.POST, template=template)
        if form.is_valid():
            te = form.save(commit=False)
            te.template = template
            te.save()
            messages.success(request, f'Enheden "{te.entity.name}" er tilføjet til skabelonen.')
            return redirect('templates_mgmt:detail', pk=template.pk)
        return render(request, 'templates_mgmt/template_entity_add.html', {
            'template': template,
            'form': form,
        })


class EditTemplateEntityView(View):
    def get(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        form = TemplateEntityForm(instance=te, template=template)
        return render(request, 'templates_mgmt/template_entity_edit.html', {
            'template': template,
            'te': te,
            'form': form,
        })

    def post(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        form = TemplateEntityForm(request.POST, instance=te, template=template)
        if form.is_valid():
            form.save()
            messages.success(request, f'Enheden er opdateret.')
            return redirect('templates_mgmt:detail', pk=template.pk)
        return render(request, 'templates_mgmt/template_entity_edit.html', {
            'template': template,
            'te': te,
            'form': form,
        })


class RemoveTemplateEntityView(View):
    def post(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        name = te.entity.name
        te.delete()
        messages.success(request, f'Enheden "{name}" er fjernet fra skabelonen.')
        return redirect('templates_mgmt:detail', pk=template.pk)


class ManageDependenciesView(View):
    def get(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        form = TemplateEntityDependencyForm(template_entity=te)
        return render(request, 'templates_mgmt/template_entity_dependencies.html', {
            'template': template,
            'te': te,
            'form': form,
        })

    def post(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        form = TemplateEntityDependencyForm(request.POST, template_entity=te)
        if form.is_valid():
            new_deps = form.cleaned_data['dependencies']
            # Validate no cycles
            cycles = validate_dependencies(te, [d.pk for d in new_deps])
            if cycles:
                cycle_names = ', '.join(str(c.entity.name) for c in cycles)
                messages.error(request, f'Cyklisk afhængighed opdaget med: {cycle_names}')
            else:
                te.dependencies.set(new_deps)
                messages.success(request, 'Afhængigheder er opdateret.')
                return redirect('templates_mgmt:detail', pk=template.pk)
        return render(request, 'templates_mgmt/template_entity_dependencies.html', {
            'template': template,
            'te': te,
            'form': form,
        })


class ManageNotificationRulesView(View):
    def get(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)
        rules = te.notification_rules.select_related('notify_user').all()
        form = NotificationRuleForm()
        return render(request, 'templates_mgmt/template_entity_notifications.html', {
            'template': template,
            'te': te,
            'rules': rules,
            'form': form,
        })

    def post(self, request, pk, te_pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        te = get_object_or_404(TemplateEntity, pk=te_pk, template=template)

        if 'delete_rule' in request.POST:
            rule_id = request.POST.get('delete_rule')
            TemplateEntityNotificationRule.objects.filter(pk=rule_id, template_entity=te).delete()
            messages.success(request, 'Notifikationsregel slettet.')
            return redirect('templates_mgmt:notifications', pk=template.pk, te_pk=te.pk)

        form = NotificationRuleForm(request.POST)
        if form.is_valid():
            rule = form.save(commit=False)
            rule.template_entity = te
            rule.save()
            messages.success(request, 'Notifikationsregel tilføjet.')
            return redirect('templates_mgmt:notifications', pk=template.pk, te_pk=te.pk)

        rules = te.notification_rules.select_related('notify_user').all()
        return render(request, 'templates_mgmt/template_entity_notifications.html', {
            'template': template,
            'te': te,
            'rules': rules,
            'form': form,
        })


class ReorderEntitiesView(View):
    """AJAX endpoint to save drag-and-drop reorder of template entities."""

    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        try:
            data = json.loads(request.body)
            order = data.get('order', [])
        except (json.JSONDecodeError, AttributeError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        for i, te_id in enumerate(order):
            TemplateEntity.objects.filter(pk=te_id, template=template).update(sort_order=i)

        return JsonResponse({'status': 'ok'})


class TemplateDuplicateView(View):
    def post(self, request, pk):
        template = get_object_or_404(OnboardingTemplate, pk=pk)
        new_template = duplicate_template(template)
        messages.success(request, f'Skabelonen "{template.name}" er kopieret til "{new_template.name}".')
        return redirect('templates_mgmt:detail', pk=new_template.pk)
