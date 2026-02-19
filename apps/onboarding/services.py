from django.utils import timezone

from .models import OnboardingTask, TaskStatus


def complete_task(task, completed_by):
    """Mark a task as completed and cascade status updates."""
    task.status = TaskStatus.COMPLETED
    task.completed_at = timezone.now()
    task.completed_by = completed_by
    task.save(update_fields=['status', 'completed_at', 'completed_by'])

    # Fire notification rules for "completed" trigger
    _fire_notification_rules(task, 'completed')

    # Cascade: unlock dependent tasks
    _cascade_status_updates(task)


def skip_task(task, skipped_by):
    """Mark a task as skipped and cascade status updates."""
    task.status = TaskStatus.SKIPPED
    task.completed_at = timezone.now()
    task.completed_by = skipped_by
    task.save(update_fields=['status', 'completed_at', 'completed_by'])

    # Fire notification rules for "skipped" trigger
    _fire_notification_rules(task, 'skipped')

    # Cascade: unlock dependent tasks
    _cascade_status_updates(task)


def start_task(task):
    """Mark a task as in progress."""
    if task.status == TaskStatus.READY:
        task.status = TaskStatus.IN_PROGRESS
        task.save(update_fields=['status'])

        # Fire notification rules for "in_progress" trigger
        _fire_notification_rules(task, 'in_progress')


def change_task_status(task, new_status, user=None):
    """Change a task to an arbitrary valid status, delegating to the right handler."""
    if new_status == task.status:
        return  # No change needed

    old_status = task.status

    if new_status == TaskStatus.COMPLETED:
        complete_task(task, user)
    elif new_status == TaskStatus.SKIPPED:
        skip_task(task, user)
    else:
        # For reversing from completed/skipped, clear completion metadata
        if old_status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
            task.completed_at = None
            task.completed_by = None

        task.status = new_status
        task.save(update_fields=['status', 'completed_at', 'completed_by'])

        # Fire notification rules for the new status
        _fire_notification_rules(task, new_status)

        # If we moved FROM a "done" status to a non-done status, dependents
        # that relied on this task being done must revert to PENDING.
        if old_status in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
            _cascade_revert_dependents(task)


def _cascade_revert_dependents(reverted_task):
    """When a task is un-completed, revert its dependents back to PENDING
    unless they are already completed or skipped themselves."""
    done_statuses = [TaskStatus.COMPLETED, TaskStatus.SKIPPED]
    for dependent in reverted_task.dependents.exclude(status__in=done_statuses):
        if dependent.is_blocked:
            dependent.status = TaskStatus.PENDING
            dependent.save(update_fields=['status'])


def _cascade_status_updates(completed_task):
    """Check dependent tasks and promote them to READY if all deps are met."""
    for dependent in completed_task.dependents.filter(status=TaskStatus.PENDING):
        if not dependent.is_blocked:
            dependent.status = TaskStatus.READY
            dependent.save(update_fields=['status'])
            # Fire notification rules for the dependent task becoming "ready"
            _fire_notification_rules(dependent, 'ready')


# ---------------------------------------------------------------------------
# Unified notification dispatch — all notifications are rule-based
# ---------------------------------------------------------------------------

STATUS_LABELS = {
    'ready': 'klar',
    'in_progress': 'i gang',
    'completed': 'færdig',
    'skipped': 'sprunget over',
}

NOTIFICATION_TYPE_MAP = {
    'ready': 'task_ready',
    'in_progress': 'task_assigned',
    'completed': 'task_completed',
    'skipped': 'task_completed',
}


def _fire_notification_rules(task, trigger_status):
    """Evaluate all notification rules for this task and send where trigger matches."""
    try:
        from apps.notifications.services import send_notification
    except ImportError:
        return
    from django.urls import reverse

    rules = task.notification_rules.select_related('notify_user').filter(
        trigger_status=trigger_status,
    )

    status_label = STATUS_LABELS.get(trigger_status, trigger_status)
    notification_type = NOTIFICATION_TYPE_MAP.get(trigger_status, 'task_completed')
    base_message = (
        f'Opgaven "{task.name}" i onboarding for '
        f'{task.onboarding.new_employee_name} er nu {status_label}.'
    )

    for rule in rules:
        # Collect direct recipients (notify_user and/or assignee)
        direct_recipients = set()
        if rule.notify_user:
            direct_recipients.add(rule.notify_user)
        if rule.notify_assignee and task.assignee:
            direct_recipients.add(task.assignee)

        # Send to direct recipients (standard message)
        for recipient in direct_recipients:
            send_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=f'Opgave {status_label}: {task.name}',
                message=base_message,
                related_onboarding=task.onboarding,
                related_task=task,
                send_email=rule.send_email,
                send_in_app=rule.send_in_app,
            )

        # Send to dependent task assignees with links to their tasks
        if rule.notify_dependent_assignees:
            dep_tasks = list(
                task.dependents.select_related('assignee').all()
            )
            # Group dependent tasks by assignee
            assignee_tasks = {}
            for dep_task in dep_tasks:
                if dep_task.assignee:
                    assignee_tasks.setdefault(dep_task.assignee, []).append(dep_task)

            for recipient, their_tasks in assignee_tasks.items():
                if recipient in direct_recipients:
                    # Already notified as direct recipient — skip duplicate
                    continue
                # Build message with links to dependent tasks
                task_links = []
                for dt in their_tasks:
                    url = reverse('onboarding:task_detail', args=[dt.onboarding_id, dt.pk])
                    task_links.append(
                        f'<a href="{url}" class="text-indigo-600 hover:text-indigo-900 '
                        f'underline">{dt.name}</a>'
                    )
                links_html = ', '.join(task_links)
                dep_message = (
                    f'{base_message}<br>'
                    f'Dine afhængige opgaver: {links_html}'
                )
                send_notification(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=f'Opgave {status_label}: {task.name}',
                    message=dep_message,
                    related_onboarding=task.onboarding,
                    related_task=task,
                    send_email=rule.send_email,
                    send_in_app=rule.send_in_app,
                )
