from django.contrib import admin
from .models import OnboardingProcess, OnboardingTask, OnboardingTaskFieldValue


class OnboardingTaskInline(admin.TabularInline):
    model = OnboardingTask
    extra = 0
    readonly_fields = ['name', 'status', 'completed_at']


class FieldValueInline(admin.TabularInline):
    model = OnboardingTaskFieldValue
    extra = 0


@admin.register(OnboardingProcess)
class OnboardingProcessAdmin(admin.ModelAdmin):
    list_display = ['new_employee_name', 'start_date', 'template', 'created_by', 'created_at']
    list_filter = ['start_date', 'template']
    search_fields = ['new_employee_name']
    inlines = [OnboardingTaskInline]


@admin.register(OnboardingTask)
class OnboardingTaskAdmin(admin.ModelAdmin):
    list_display = ['name', 'onboarding', 'status', 'assignee', 'deadline']
    list_filter = ['status', 'assignee']
    search_fields = ['name']
    inlines = [FieldValueInline]
