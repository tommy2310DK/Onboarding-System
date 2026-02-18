from django.urls import path
from . import views

app_name = 'entities'

urlpatterns = [
    path('', views.EntityListView.as_view(), name='list'),
    path('create/', views.EntityCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EntityDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.EntityUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.EntityDeleteView.as_view(), name='delete'),
]
