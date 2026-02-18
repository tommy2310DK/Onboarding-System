from django.contrib import admin
from .models import Entity, CustomFieldDefinition


class CustomFieldInline(admin.TabularInline):
    model = CustomFieldDefinition
    extra = 1


@admin.register(Entity)
class EntityAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'created_at']
    list_filter = ['category']
    search_fields = ['name', 'description']
    inlines = [CustomFieldInline]
