from django.utils import timezone

from .models import OnboardingTask, TaskStatus


def complete_task(task, completed_by):
    """Mark a task as completed and cascade status updates."""
    task.status = TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.completed_by = completed_by
    task.save(update_fields=['status', 'completed_at', 'completed_by'])

    # Send notifications for this task completion
    _send_completion_notifications(task)

    # Cascade: unlock dependent tasks
    _cascade_status_updates(task)

    # Check if entire onboarding is complete
    if task.onboarding.is_complete:
        _send_onboarding_complete_notification(task.onboarding)


def skip_task(task, skipped_by):
    """Mark a task as skipped and cascade status updates."""
    task.status = TaskStatus.SKIPPED
    task.completed_at = timezone.now()
    task.completed_by = skipped_by
    task.save(update_fields=['status', 'completed_at', 'completed_by'])

    # Cascade: unlock dependent tasks
    _cascade_status_updates(task)

    if task.onboarding.is_complete:
        _send_onboarding_complete_notification(task.onboarding)


def start_task(task):
    """Mark a task as in progress."""
    if task.status == TaskStatus.READY:
        task.status = TaskStatus.IN_PROGRESS
        task.save(update_fields=['status'])


def _cascade_status_updates(completed_task):
    """Check dependent tasks and promote them to READY if all deps are met."""
    for dependent in completed_task.dependents.filter(status=TaskStatus.PENDING):
        if not dependent.is_blocked:
            dependent.status = TaskStatus.READY
            dependent.save(update_fields=['status'])
            # Notify the assignee that their task is now ready
            _send_task_ready_notification(dependent)


def _send_completion_notifications(task):
    """Send notifications based on task notification rules."""
    try:
        from apps.notifications.services import send_notification
        from apps.notifications.models import NotificationType
    except ImportError:
        return

    for rule in task.notification_rules.select_related('notify_user').all():
        send_notification(
            recipient=rule.notify_user,
            notification_type=NotificationType.TASK_COMPLETED,
            title=f'Opgave færdig: {task.name}',
            message=(
                f'Opgaven "{task.name}" i onboarding for '
                f'{task.onboarding.new_employee_name} er blevet fuldført.'
            ),
            related_onboarding=task.onboarding,
            related_task=task,
            send_email=rule.send_email,
            send_in_app=rule.send_in_app,
        )


def _send_task_ready_notification(task):
    """Notify the assignee that their task is now ready."""
    if not task.assignee:
        return

    try:
        from apps.notifications.services import send_notification
        from apps.notifications.models import NotificationType
    except ImportError:
        return

    send_notification(
        recipient=task.assignee,
        notification_type=NotificationType.TASK_READY,
        title=f'Opgave klar: {task.name}',
        message=(
            f'Opgaven "{task.name}" i onboarding for '
            f'{task.onboarding.new_employee_name} er nu klar til at blive udført.'
        ),
        related_onboarding=task.onboarding,
        related_task=task,
        send_email=True,
        send_in_app=True,
    )


def _send_onboarding_complete_notification(onboarding):
    """Notify the creator that the onboarding is complete."""
    if not onboarding.created_by:
        return

    try:
        from apps.notifications.services import send_notification
        from apps.notifications.models import NotificationType
    except ImportError:
        return

    send_notification(
        recipient=onboarding.created_by,
        notification_type=NotificationType.ONBOARDING_COMPLETED,
        title=f'Onboarding færdig: {onboarding.new_employee_name}',
        message=(
            f'Alle opgaver i onboarding for {onboarding.new_employee_name} '
            f'er nu fuldført.'
        ),
        related_onboarding=onboarding,
        send_email=True,
        send_in_app=True,
    )
