from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from .forms import CustomFieldFormSet, EntityForm
from .models import Category, Entity


class EntityListView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        entities = Entity.objects.select_related('category').all()
        if query:
            entities = entities.filter(name__icontains=query) | entities.filter(category__name__icontains=query)
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


# --- Category CRUD ---

class CategoryListView(View):
    def get(self, request):
        categories = Category.objects.annotate(
            entity_count=models.Count('entities')
        ).all()
        return render(request, 'entities/category_list.html', {
            'categories': categories,
        })


class CategoryCreateView(View):
    def get(self, request):
        return render(request, 'entities/category_form.html', {
            'is_create': True,
        })

    def post(self, request):
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Kategori-navn er påkrævet.')
            return render(request, 'entities/category_form.html', {
                'is_create': True, 'name_value': name,
            })
        if Category.objects.filter(name=name).exists():
            messages.error(request, f'Kategorien "{name}" findes allerede.')
            return render(request, 'entities/category_form.html', {
                'is_create': True, 'name_value': name,
            })
        cat = Category.objects.create(name=name)
        messages.success(request, f'Kategorien "{cat.name}" er oprettet.')
        return redirect('entities:category_list')


class CategoryUpdateView(View):
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        return render(request, 'entities/category_form.html', {
            'category': category,
            'is_create': False,
            'name_value': category.name,
        })

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Kategori-navn er påkrævet.')
            return render(request, 'entities/category_form.html', {
                'category': category, 'is_create': False, 'name_value': name,
            })
        if Category.objects.filter(name=name).exclude(pk=pk).exists():
            messages.error(request, f'Kategorien "{name}" findes allerede.')
            return render(request, 'entities/category_form.html', {
                'category': category, 'is_create': False, 'name_value': name,
            })
        category.name = name
        category.save(update_fields=['name'])
        messages.success(request, f'Kategorien er omdøbt til "{name}".')
        return redirect('entities:category_list')


class CategoryDeleteView(View):
    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        entity_count = category.entities.count()
        return render(request, 'entities/category_confirm_delete.html', {
            'category': category,
            'entity_count': entity_count,
        })

    def post(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        name = category.name
        category.delete()
        messages.success(request, f'Kategorien "{name}" er slettet.')
        return redirect('entities:category_list')


class CategoryCreateAjaxView(View):
    """AJAX endpoint to create a category inline from the entity form."""

    def post(self, request):
        import json as json_mod
        try:
            data = json_mod.loads(request.body)
        except (json_mod.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        name = data.get('name', '').strip()
        if not name:
            return JsonResponse({'error': 'Navn er påkrævet'}, status=400)

        cat, created = Category.objects.get_or_create(name=name)
        return JsonResponse({'id': cat.pk, 'name': cat.name, 'created': created})
