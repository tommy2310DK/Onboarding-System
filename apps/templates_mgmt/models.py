from django.db import models


class OnboardingTemplate(models.Model):
    name = models.CharField(max_length=300, verbose_name='Navn')
    description = models.TextField(blank=True, verbose_name='Beskrivelse')
    is_active = models.BooleanField(default=True, verbose_name='Aktiv')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Onboarding-skabelon'
        verbose_name_plural = 'Onboarding-skabeloner'

    def __str__(self):
        return self.name


class TemplateEntity(models.Model):
    template = models.ForeignKey(
        OnboardingTemplate, on_delete=models.CASCADE,
        related_name='template_entities'
    )
    entity = models.ForeignKey(
        'entities.Entity', on_delete=models.CASCADE,
        related_name='template_usages'
    )
    days_before_start = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Dage før start',
        help_text='Antal dage før startdato denne opgave skal være færdig'
    )
    default_assignee = models.ForeignKey(
        'core.SystemUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_template_entities',
        verbose_name='Standard-ansvarlig'
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Sortering')
    dependencies = models.ManyToManyField(
        'self', symmetrical=False, blank=True,
        related_name='dependents',
        verbose_name='Afhængigheder'
    )

    class Meta:
        ordering = ['sort_order']
        unique_together = ['template', 'entity']
        verbose_name = 'Skabelon-enhed'
        verbose_name_plural = 'Skabelon-enheder'

    def __str__(self):
        return f"{self.template.name} → {self.entity.name}"


class TriggerStatus(models.TextChoices):
    READY = 'ready', 'Klar'
    IN_PROGRESS = 'in_progress', 'I gang'
    COMPLETED = 'completed', 'Færdig'
    SKIPPED = 'skipped', 'Sprunget over'


class TemplateEntityNotificationRule(models.Model):
    template_entity = models.ForeignKey(
        TemplateEntity, on_delete=models.CASCADE,
        related_name='notification_rules'
    )
    notify_user = models.ForeignKey(
        'core.SystemUser', on_delete=models.CASCADE,
        null=True, blank=True,
        related_name='template_notification_rules',
        verbose_name='Bruger'
    )
    notify_assignee = models.BooleanField(
        default=False,
        verbose_name='Notificer ansvarlig',
        help_text='Send notifikation til den ansvarlige for opgaven',
    )
    trigger_status = models.CharField(
        max_length=20,
        choices=TriggerStatus.choices,
        default=TriggerStatus.COMPLETED,
        verbose_name='Ved status',
        help_text='Send notifikation når opgaven skifter til denne status',
    )
    send_email = models.BooleanField(default=True, verbose_name='Send email')
    send_in_app = models.BooleanField(default=True, verbose_name='In-app notifikation')

    class Meta:
        verbose_name = 'Notifikationsregel'
        verbose_name_plural = 'Notifikationsregler'

    def __str__(self):
        target = self.notify_user or 'Ansvarlig'
        return f"Notificer {target} når {self.template_entity} bliver {self.get_trigger_status_display()}"
