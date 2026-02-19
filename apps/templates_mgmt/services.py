import json
from datetime import timedelta

from django.db import transaction


def would_create_cycle(template_entity, proposed_dependency):
    """Check if adding proposed_dependency would create a cycle."""
    visited = set()
    stack = [proposed_dependency]
    while stack:
        current = stack.pop()
        if current.id == template_entity.id:
            return True
        if current.id not in visited:
            visited.add(current.id)
            stack.extend(current.dependencies.all())
    return False


def validate_dependencies(template_entity, dependency_ids):
    """Validate a set of proposed dependencies, returning any that would create cycles."""
    from .models import TemplateEntity
    cycles = []
    for dep_id in dependency_ids:
        dep = TemplateEntity.objects.get(pk=dep_id)
        if would_create_cycle(template_entity, dep):
            cycles.append(dep)
    return cycles


@transaction.atomic
def create_onboarding_from_template(template, new_employee_name, new_employee_email,
                                     new_employee_department, new_employee_position,
                                     start_date, created_by):
    """Instantiate an onboarding process from a template."""
    from apps.onboarding.models import (
        OnboardingProcess, OnboardingTask, OnboardingTaskFieldValue,
        TaskNotificationRule, TaskStatus,
    )

    process = OnboardingProcess.objects.create(
        template=template,
        new_employee_name=new_employee_name,
        new_employee_email=new_employee_email,
        new_employee_department=new_employee_department,
        new_employee_position=new_employee_position,
        start_date=start_date,
        created_by=created_by,
    )

    # Map template_entity.id -> OnboardingTask for dependency wiring
    te_to_task = {}

    for te in template.template_entities.select_related('entity', 'default_assignee').all():
        # Compute deadline
        deadline = None
        if te.days_before_start is not None:
            deadline = start_date - timedelta(days=te.days_before_start)

        task = OnboardingTask.objects.create(
            onboarding=process,
            source_template_entity=te,
            entity=te.entity,
            name=te.entity.name,
            description=te.entity.description,
            status=TaskStatus.PENDING,
            assignee=te.default_assignee,
            deadline=deadline,
            sort_order=te.sort_order,
        )
        te_to_task[te.id] = task

        # Create field values
        for field_def in te.entity.custom_fields.all():
            if field_def.field_type == 'todolist':
                # default_value stores newline-separated items; convert to JSON
                if field_def.default_value.strip():
                    lines = [l.strip() for l in field_def.default_value.split('\n') if l.strip()]
                    initial_text = json.dumps(
                        [{'text': t, 'done': False} for t in lines],
                        ensure_ascii=False,
                    )
                else:
                    initial_text = '[]'
            elif field_def.field_type == 'text':
                initial_text = field_def.default_value
            else:
                initial_text = ''
            OnboardingTaskFieldValue.objects.create(
                task=task,
                field_definition=field_def,
                value_text=initial_text,
                value_number=None,
                value_checkbox=False,
            )

        # Copy notification rules
        for rule in te.notification_rules.all():
            TaskNotificationRule.objects.create(
                task=task,
                notify_user=rule.notify_user,
                notify_assignee=rule.notify_assignee,
                notify_dependent_assignees=rule.notify_dependent_assignees,
                trigger_status=rule.trigger_status,
                send_email=rule.send_email,
                send_in_app=rule.send_in_app,
            )

    # Wire up dependencies
    for te in template.template_entities.prefetch_related('dependencies').all():
        task = te_to_task[te.id]
        for dep_te in te.dependencies.all():
            if dep_te.id in te_to_task:
                task.dependencies.add(te_to_task[dep_te.id])

    # Resolve initial statuses: tasks with no dependencies become READY
    from apps.onboarding.services import _fire_notification_rules

    for task in process.tasks.all():
        if not task.dependencies.exists():
            task.status = TaskStatus.READY
            task.save(update_fields=['status'])
            _fire_notification_rules(task, 'ready')

    return process


@transaction.atomic
def duplicate_template(template):
    """Create a deep copy of a template, including all entities, dependencies, and notification rules."""
    from .models import OnboardingTemplate, TemplateEntity, TemplateEntityNotificationRule

    # Create the new template
    new_template = OnboardingTemplate.objects.create(
        name=f"{template.name} (kopi)",
        description=template.description,
    )

    # Map old TemplateEntity pk -> new TemplateEntity for dependency wiring
    old_to_new = {}

    for te in template.template_entities.select_related('entity', 'default_assignee').all():
        new_te = TemplateEntity.objects.create(
            template=new_template,
            entity=te.entity,
            days_before_start=te.days_before_start,
            default_assignee=te.default_assignee,
            sort_order=te.sort_order,
        )
        old_to_new[te.pk] = new_te

        # Copy notification rules
        for rule in te.notification_rules.all():
            TemplateEntityNotificationRule.objects.create(
                template_entity=new_te,
                notify_user=rule.notify_user,
                notify_assignee=rule.notify_assignee,
                notify_dependent_assignees=rule.notify_dependent_assignees,
                trigger_status=rule.trigger_status,
                send_email=rule.send_email,
                send_in_app=rule.send_in_app,
            )

    # Wire up dependencies using the mapping
    for te in template.template_entities.prefetch_related('dependencies').all():
        new_te = old_to_new[te.pk]
        for dep in te.dependencies.all():
            if dep.pk in old_to_new:
                new_te.dependencies.add(old_to_new[dep.pk])

    return new_template
