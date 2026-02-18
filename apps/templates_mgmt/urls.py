from django.urls import path
from . import views

app_name = 'templates_mgmt'

urlpatterns = [
    path('', views.TemplateListView.as_view(), name='list'),
    path('create/', views.TemplateCreateView.as_view(), name='create'),
    path('<int:pk>/', views.TemplateDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.TemplateUpdateView.as_view(), name='edit'),
    path('<int:pk>/delete/', views.TemplateDeleteView.as_view(), name='delete'),
    path('<int:pk>/add-entity/', views.AddEntityToTemplateView.as_view(), name='add_entity'),
    path('<int:pk>/entities/<int:te_pk>/edit/', views.EditTemplateEntityView.as_view(), name='edit_entity'),
    path('<int:pk>/entities/<int:te_pk>/remove/', views.RemoveTemplateEntityView.as_view(), name='remove_entity'),
    path('<int:pk>/entities/<int:te_pk>/dependencies/', views.ManageDependenciesView.as_view(), name='dependencies'),
    path('<int:pk>/entities/<int:te_pk>/notifications/', views.ManageNotificationRulesView.as_view(), name='notifications'),
    path('<int:pk>/reorder/', views.ReorderEntitiesView.as_view(), name='reorder'),
    path('<int:pk>/duplicate/', views.TemplateDuplicateView.as_view(), name='duplicate'),
]
