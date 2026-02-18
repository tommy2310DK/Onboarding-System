from django.contrib import admin
from .models import SystemUser


@admin.register(SystemUser)
class SystemUserAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'department', 'title', 'auth_method', 'is_active']
    list_filter = ['is_active', 'department', 'auth_method']
    search_fields = ['name', 'email', 'department', 'title']
    readonly_fields = ['created_at', 'updated_at']
