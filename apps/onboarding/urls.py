from django.urls import path
from . import views

app_name = 'onboarding'

urlpatterns = [
    path('', views.OnboardingListView.as_view(), name='list'),
    path('create/', views.OnboardingCreateView.as_view(), name='create'),
    path('<int:pk>/', views.OnboardingDetailView.as_view(), name='detail'),
    path('<int:pk>/delete/', views.OnboardingDeleteView.as_view(), name='delete'),
    path('<int:pk>/tasks/<int:task_pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<int:pk>/tasks/<int:task_pk>/complete/', views.TaskCompleteView.as_view(), name='task_complete'),
    path('<int:pk>/tasks/<int:task_pk>/skip/', views.TaskSkipView.as_view(), name='task_skip'),
    path('<int:pk>/tasks/<int:task_pk>/start/', views.TaskStartView.as_view(), name='task_start'),
    path('<int:pk>/tasks/<int:task_pk>/edit/', views.TaskEditView.as_view(), name='task_edit'),
]
