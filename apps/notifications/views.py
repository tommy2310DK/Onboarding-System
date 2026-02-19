from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.models import SystemUser
from .models import Notification
from .services import get_unread_count


def _get_current_user(request):
    user_id = request.session.get('current_user_id')
    if user_id:
        try:
            return SystemUser.objects.get(id=user_id, is_active=True)
        except SystemUser.DoesNotExist:
            pass
    return None


class NotificationListView(View):
    def get(self, request):
        user = _get_current_user(request)
        if not user:
            return render(request, 'notifications/notification_list.html', {
                'notifications': [],
            })

        # Sorting: default newest first, allow ?sort=oldest
        sort = request.GET.get('sort', 'newest')
        if sort == 'oldest':
            ordering = 'created_at'
        else:
            ordering = '-created_at'
            sort = 'newest'

        notifications = Notification.objects.filter(recipient=user).select_related(
            'related_onboarding', 'related_task'
        ).order_by(ordering)[:50]

        has_read = Notification.objects.filter(recipient=user, is_read=True).exists()

        return render(request, 'notifications/notification_list.html', {
            'notifications': notifications,
            'current_sort': sort,
            'has_read': has_read,
        })


class UnreadCountView(View):
    def get(self, request):
        user = _get_current_user(request)
        if not user:
            return HttpResponse('')
        count = get_unread_count(user)
        if count > 0:
            return HttpResponse(
                f'<span class="absolute -top-1 -right-1 bg-red-500 text-white text-xs '
                f'rounded-full w-5 h-5 flex items-center justify-center badge-pulse">'
                f'{count}</span>'
            )
        return HttpResponse('')


class MarkReadView(View):
    def post(self, request, pk):
        user = _get_current_user(request)
        if user:
            notification = get_object_or_404(Notification, pk=pk, recipient=user)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
        if request.htmx:
            return HttpResponse('')
        return redirect('notifications:list')


class MarkAllReadView(View):
    def post(self, request):
        user = _get_current_user(request)
        if user:
            Notification.objects.filter(recipient=user, is_read=False).update(is_read=True)
        return redirect('notifications:list')


class DeleteNotificationView(View):
    def post(self, request, pk):
        user = _get_current_user(request)
        if user:
            Notification.objects.filter(pk=pk, recipient=user).delete()
        return redirect('notifications:list')


class DeleteAllReadView(View):
    def post(self, request):
        user = _get_current_user(request)
        if user:
            Notification.objects.filter(recipient=user, is_read=True).delete()
        return redirect('notifications:list')
