from django.core.mail import send_mail
from django.conf import settings

from .models import Notification, NotificationType


def send_notification(recipient, notification_type, title, message,
                      related_onboarding=None, related_task=None,
                      send_email=True, send_in_app=True):
    """Central notification dispatch function."""
    notification = None

    if send_in_app:
        notification = Notification.objects.create(
            recipient=recipient,
            notification_type=notification_type,
            title=title,
            message=message,
            related_onboarding=related_onboarding,
            related_task=related_task,
        )

    if send_email and recipient.email:
        try:
            send_mail(
                subject=title,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient.email],
                fail_silently=True,
            )
            if notification:
                notification.email_sent = True
                notification.save(update_fields=['email_sent'])
        except Exception:
            pass

    return notification


def get_unread_count(user):
    """Get unread notification count for a user."""
    return Notification.objects.filter(recipient=user, is_read=False).count()
