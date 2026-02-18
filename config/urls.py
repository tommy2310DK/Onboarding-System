from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.core.urls')),
    path('entities/', include('apps.entities.urls')),
    path('templates/', include('apps.templates_mgmt.urls')),
    path('onboarding/', include('apps.onboarding.urls')),
    path('notifications/', include('apps.notifications.urls')),
]
