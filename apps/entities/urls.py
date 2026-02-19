from django.urls import path
from . import views

app_name = 'entities'

urlpatterns = [
    path('', views.EntityListView.as_view(), name='list'),
    path('create/', views.EntityCreateView.as_view(), name='create'),
    path('<int:pk>/', views.EntityDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.EntityUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.EntityDeleteView.as_view(), name='delete'),
    # Categories
    path('categories/', views.CategoryListView.as_view(), name='category_list'),
    path('categories/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('categories/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_edit'),
    path('categories/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),
    path('categories/create-ajax/', views.CategoryCreateAjaxView.as_view(), name='category_create_ajax'),
]
