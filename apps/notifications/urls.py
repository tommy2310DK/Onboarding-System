from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='list'),
    path('unread-count/', views.UnreadCountView.as_view(), name='unread_count'),
    path('<int:pk>/mark-read/', views.MarkReadView.as_view(), name='mark_read'),
    path('<int:pk>/delete/', views.DeleteNotificationView.as_view(), name='delete'),
    path('mark-all-read/', views.MarkAllReadView.as_view(), name='mark_all_read'),
    path('delete-all-read/', views.DeleteAllReadView.as_view(), name='delete_all_read'),
]
