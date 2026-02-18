from django.db import models
from django.utils import timezone


class TaskStatus(models.TextChoices):
    PENDING = 'pending', 'Afventer'
    READY = 'ready', 'Klar'
    IN_PROGRESS = 'in_progress', 'I gang'
    COMPLETED = 'completed', 'Færdig'
    SKIPPED = 'skipped', 'Sprunget over'


class OnboardingProcess(models.Model):
    template = models.ForeignKey(
        'templates_mgmt.OnboardingTemplate', on_delete=models.SET_NULL,
        null=True, related_name='instances'
    )
    new_employee_name = models.CharField(max_length=300, verbose_name='Medarbejder navn')
    new_employee_email = models.EmailField(blank=True, verbose_name='Email')
    new_employee_department = models.CharField(max_length=200, blank=True, verbose_name='Afdeling')
    new_employee_position = models.CharField(max_length=300, blank=True, verbose_name='Stilling')
    start_date = models.DateField(verbose_name='Startdato',
                                   help_text='Dato hvor den nye medarbejder starter')
    notes = models.TextField(blank=True, verbose_name='Noter')
    created_by = models.ForeignKey(
        'core.SystemUser', on_delete=models.SET_NULL,
        null=True, related_name='created_onboardings',
        verbose_name='Oprettet af'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date']
        verbose_name = 'Onboarding-proces'
        verbose_name_plural = 'Onboarding-processer'

    def __str__(self):
        return f"Onboarding: {self.new_employee_name} (start: {self.start_date})"

    @property
    def progress_percentage(self):
        tasks = self.tasks.all()
        if not tasks.exists():
            return 0
        completed = tasks.filter(
            status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        ).count()
        return int((completed / tasks.count()) * 100)

    @property
    def is_complete(self):
        return self.progress_percentage == 100

    @property
    def total_tasks(self):
        return self.tasks.count()

    @property
    def completed_tasks(self):
        return self.tasks.filter(
            status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        ).count()


class OnboardingTask(models.Model):
    onboarding = models.ForeignKey(
        OnboardingProcess, on_delete=models.CASCADE, related_name='tasks'
    )
    source_template_entity = models.ForeignKey(
        'templates_mgmt.TemplateEntity', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    entity = models.ForeignKey(
        'entities.Entity', on_delete=models.SET_NULL,
        null=True, related_name='onboarding_tasks'
    )
    name = models.CharField(max_length=300)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20, choices=TaskStatus.choices, default=TaskStatus.PENDING,
        verbose_name='Status'
    )
    assignee = models.ForeignKey(
        'core.SystemUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_tasks',
        verbose_name='Ansvarlig'
    )
    deadline = models.DateField(null=True, blank=True, verbose_name='Deadline')
    deadline_overridden = models.BooleanField(default=False)
    dependencies = models.ManyToManyField(
        'self', symmetrical=False, blank=True, related_name='dependents'
    )
    sort_order = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        'core.SystemUser', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='completed_tasks'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order']
        verbose_name = 'Onboarding-opgave'
        verbose_name_plural = 'Onboarding-opgaver'

    def __str__(self):
        return f"{self.onboarding.new_employee_name} → {self.name}"

    @property
    def is_blocked(self):
        return self.dependencies.exclude(
            status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        ).exists()

    @property
    def is_overdue(self):
        if self.deadline and self.status not in [TaskStatus.COMPLETED, TaskStatus.SKIPPED]:
            return timezone.now().date() > self.deadline
        return False

    @property
    def status_color(self):
        return {
            TaskStatus.PENDING: 'gray',
            TaskStatus.READY: 'blue',
            TaskStatus.IN_PROGRESS: 'yellow',
            TaskStatus.COMPLETED: 'green',
            TaskStatus.SKIPPED: 'gray',
        }.get(self.status, 'gray')


class OnboardingTaskFieldValue(models.Model):
    task = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE, related_name='field_values'
    )
    field_definition = models.ForeignKey(
        'entities.CustomFieldDefinition', on_delete=models.CASCADE
    )
    value_text = models.TextField(blank=True, default='')
    value_number = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    value_checkbox = models.BooleanField(default=False)

    class Meta:
        unique_together = ['task', 'field_definition']

    def __str__(self):
        return f"{self.task.name} → {self.field_definition.name}"

    def get_value(self):
        ft = self.field_definition.field_type
        if ft == 'text':
            return self.value_text
        elif ft == 'number':
            return self.value_number
        elif ft == 'checkbox':
            return self.value_checkbox
        return self.value_text


class TaskNotificationRule(models.Model):
    task = models.ForeignKey(
        OnboardingTask, on_delete=models.CASCADE, related_name='notification_rules'
    )
    notify_user = models.ForeignKey(
        'core.SystemUser', on_delete=models.CASCADE
    )
    send_email = models.BooleanField(default=True)
    send_in_app = models.BooleanField(default=True)

    class Meta:
        unique_together = ['task', 'notify_user']
