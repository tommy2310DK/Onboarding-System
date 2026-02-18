from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import CustomFieldFormSet, EntityForm
from .models import Entity


class EntityListView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        entities = Entity.objects.all()
        if query:
            entities = entities.filter(name__icontains=query) | entities.filter(category__icontains=query)
            entities = entities.distinct()
        return render(request, 'entities/entity_list.html', {
            'entities': entities,
            'query': query,
        })


class EntityCreateView(View):
    def get(self, request):
        form = EntityForm()
        formset = CustomFieldFormSet()
        return render(request, 'entities/entity_form.html', {
            'form': form,
            'formset': formset,
            'is_create': True,
        })

    def post(self, request):
        form = EntityForm(request.POST)
        formset = CustomFieldFormSet(request.POST)
        if form.is_valid():
            entity = form.save()
            formset = CustomFieldFormSet(request.POST, instance=entity)
            if formset.is_valid():
                formset.save()
                messages.success(request, f'Enheden "{entity.name}" er oprettet.')
                return redirect('entities:detail', pk=entity.pk)
        return render(request, 'entities/entity_form.html', {
            'form': form,
            'formset': formset,
            'is_create': True,
        })


class EntityDetailView(View):
    def get(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk)
        return render(request, 'entities/entity_detail.html', {
            'entity': entity,
        })


class EntityUpdateView(View):
    def get(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk)
        form = EntityForm(instance=entity)
        formset = CustomFieldFormSet(instance=entity)
        return render(request, 'entities/entity_form.html', {
            'form': form,
            'formset': formset,
            'entity': entity,
            'is_create': False,
        })

    def post(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk)
        form = EntityForm(request.POST, instance=entity)
        formset = CustomFieldFormSet(request.POST, instance=entity)
        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, f'Enheden "{entity.name}" er opdateret.')
            return redirect('entities:detail', pk=entity.pk)
        return render(request, 'entities/entity_form.html', {
            'form': form,
            'formset': formset,
            'entity': entity,
            'is_create': False,
        })


class EntityDeleteView(View):
    def get(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk)
        return render(request, 'entities/entity_confirm_delete.html', {
            'entity': entity,
        })

    def post(self, request, pk):
        entity = get_object_or_404(Entity, pk=pk)
        name = entity.name
        entity.delete()
        messages.success(request, f'Enheden "{name}" er slettet.')
        return redirect('entities:list')
