from django.db import models


class NotificationType(models.TextChoices):
    TASK_COMPLETED = 'task_completed', 'Opgave færdig'
    TASK_ASSIGNED = 'task_assigned', 'Opgave tildelt'
    TASK_READY = 'task_ready', 'Opgave klar'
    TASK_OVERDUE = 'task_overdue', 'Opgave forsinket'
    ONBOARDING_COMPLETED = 'onboarding_completed', 'Onboarding færdig'


class Notification(models.Model):
    recipient = models.ForeignKey(
        'core.SystemUser', on_delete=models.CASCADE,
        related_name='notifications', verbose_name='Modtager'
    )
    notification_type = models.CharField(
        max_length=30, choices=NotificationType.choices,
        verbose_name='Type'
    )
    title = models.CharField(max_length=300, verbose_name='Titel')
    message = models.TextField(verbose_name='Besked')
    related_onboarding = models.ForeignKey(
        'onboarding.OnboardingProcess', on_delete=models.CASCADE,
        null=True, blank=True
    )
    related_task = models.ForeignKey(
        'onboarding.OnboardingTask', on_delete=models.CASCADE,
        null=True, blank=True
    )
    is_read = models.BooleanField(default=False, verbose_name='Læst')
    email_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notifikation'
        verbose_name_plural = 'Notifikationer'

    def __str__(self):
        return f"{self.recipient}: {self.title}"
