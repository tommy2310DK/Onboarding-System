from django.contrib import admin
from .models import OnboardingTemplate, TemplateEntity, TemplateEntityNotificationRule


class TemplateEntityInline(admin.TabularInline):
    model = TemplateEntity
    extra = 1


class NotificationRuleInline(admin.TabularInline):
    model = TemplateEntityNotificationRule
    extra = 1


@admin.register(OnboardingTemplate)
class OnboardingTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    inlines = [TemplateEntityInline]


@admin.register(TemplateEntity)
class TemplateEntityAdmin(admin.ModelAdmin):
    list_display = ['template', 'entity', 'days_before_start', 'default_assignee', 'sort_order']
    list_filter = ['template']
    inlines = [NotificationRuleInline]
