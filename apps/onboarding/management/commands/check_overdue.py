from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.notifications.models import NotificationType
from apps.notifications.services import send_notification
from apps.onboarding.models import OnboardingTask, TaskStatus


class Command(BaseCommand):
    help = 'Check for overdue tasks and send notifications'

    def handle(self, *args, **options):
        today = timezone.now().date()
        overdue_tasks = OnboardingTask.objects.filter(
            deadline__lt=today,
            status__in=[TaskStatus.PENDING, TaskStatus.READY, TaskStatus.IN_PROGRESS],
        ).select_related('assignee', 'onboarding')

        count = 0
        for task in overdue_tasks:
            if task.assignee:
                send_notification(
                    recipient=task.assignee,
                    notification_type=NotificationType.TASK_OVERDUE,
                    title=f'Forsinket opgave: {task.name}',
                    message=(
                        f'Opgaven "{task.name}" i onboarding for '
                        f'{task.onboarding.new_employee_name} er forsinket. '
                        f'Deadline var {task.deadline}.'
                    ),
                    related_onboarding=task.onboarding,
                    related_task=task,
                    send_email=True,
                    send_in_app=True,
                )
                count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Checked overdue tasks. Sent {count} notifications.')
        )
