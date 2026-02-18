from apps.core.models import SystemUser


def current_user(request):
    user_id = request.session.get('current_user_id')
    user = None
    if user_id:
        try:
            user = SystemUser.objects.get(id=user_id, is_active=True)
        except SystemUser.DoesNotExist:
            pass
    return {
        'current_user': user,
        'all_users': SystemUser.objects.filter(is_active=True),
    }
