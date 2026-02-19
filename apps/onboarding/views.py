import json

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View

from apps.core.models import SystemUser
from apps.templates_mgmt.services import create_onboarding_from_template
from .forms import OnboardingCreateForm, TaskEditForm
from .models import OnboardingProcess, OnboardingTask, OnboardingTaskFieldValue, TaskStatus
from .services import change_task_status, complete_task, skip_task, start_task


def _get_tasks_with_overview(process):
    """Fetch tasks for a process and pre-compute overview_fields on each."""
    tasks = list(
        process.tasks
        .select_related('assignee', 'entity')
        .prefetch_related('dependencies', 'field_values__field_definition')
        .all()
    )
    for task in tasks:
        task.overview_fields = [
            fv for fv in task.field_values.all()
            if fv.field_definition.show_on_overview
        ]
    return tasks


class OnboardingListView(View):
    def get(self, request):
        processes = OnboardingProcess.objects.prefetch_related('tasks').all()

        status_filter = request.GET.get('status', '')
        if status_filter == 'active':
            # Exclude fully completed
            processes = [p for p in processes if not p.is_complete]
        elif status_filter == 'completed':
            processes = [p for p in processes if p.is_complete]

        return render(request, 'onboarding/onboarding_list.html', {
            'processes': processes,
            'status_filter': status_filter,
        })


class OnboardingCreateView(View):
    def get(self, request):
        form = OnboardingCreateForm()
        return render(request, 'onboarding/onboarding_create.html', {'form': form})

    def post(self, request):
        form = OnboardingCreateForm(request.POST)
        if form.is_valid():
            current_user = None
            user_id = request.session.get('current_user_id')
            if user_id:
                try:
                    current_user = SystemUser.objects.get(id=user_id)
                except SystemUser.DoesNotExist:
                    pass

            process = create_onboarding_from_template(
                template=form.cleaned_data['template'],
                new_employee_name=form.cleaned_data['new_employee_name'],
                new_employee_email=form.cleaned_data['new_employee_email'],
                new_employee_department=form.cleaned_data['new_employee_department'],
                new_employee_position=form.cleaned_data['new_employee_position'],
                start_date=form.cleaned_data['start_date'],
                created_by=current_user,
            )
            if form.cleaned_data['notes']:
                process.notes = form.cleaned_data['notes']
                process.save(update_fields=['notes'])

            messages.success(request, f'Onboarding for "{process.new_employee_name}" er oprettet.')
            return redirect('onboarding:detail', pk=process.pk)
        return render(request, 'onboarding/onboarding_create.html', {'form': form})


class OnboardingDeleteView(View):
    def get(self, request, pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task_count = process.tasks.count()
        completed_count = process.tasks.filter(
            status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED]
        ).count()
        return render(request, 'onboarding/onboarding_confirm_delete.html', {
            'process': process,
            'task_count': task_count,
            'completed_count': completed_count,
        })

    def post(self, request, pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        name = process.new_employee_name
        process.delete()
        messages.success(request, f'Onboarding for "{name}" er slettet.')
        return redirect('onboarding:list')


class OnboardingDetailView(View):
    SORT_FIELDS = {
        'status': 'status',
        'name': 'name',
        'assignee': 'assignee__name',
        'deadline': 'deadline',
    }

    # Custom ordering for status so it follows the logical flow
    STATUS_ORDER = {
        'pending': 0, 'ready': 1, 'in_progress': 2,
        'completed': 3, 'skipped': 4,
    }

    def get(self, request, pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        tasks = (
            process.tasks
            .select_related('assignee', 'entity')
            .prefetch_related('dependencies', 'field_values__field_definition')
            .all()
        )

        sort_by = request.GET.get('sort', '')
        sort_dir = request.GET.get('dir', 'asc')

        if sort_by == 'status':
            # Custom sort via Python for logical status ordering
            reverse = (sort_dir == 'desc')
            tasks = sorted(tasks, key=lambda t: self.STATUS_ORDER.get(t.status, 99), reverse=reverse)
        elif sort_by in self.SORT_FIELDS:
            db_field = self.SORT_FIELDS[sort_by]
            order_field = f'-{db_field}' if sort_dir == 'desc' else db_field
            # Nulls last for optional fields
            if sort_by in ('assignee', 'deadline'):
                from django.db.models import F
                if sort_dir == 'desc':
                    tasks = tasks.order_by(F(db_field).desc(nulls_last=True))
                else:
                    tasks = tasks.order_by(F(db_field).asc(nulls_last=True))
            else:
                tasks = tasks.order_by(order_field)

        # Pre-compute overview field values for each task
        # (field_values where field_definition.show_on_overview=True)
        if isinstance(tasks, list):
            task_list = tasks
        else:
            task_list = list(tasks)

        for task in task_list:
            task.overview_fields = [
                fv for fv in task.field_values.all()
                if fv.field_definition.show_on_overview
            ]

        return render(request, 'onboarding/onboarding_detail.html', {
            'process': process,
            'tasks': task_list,
            'sort_by': sort_by,
            'sort_dir': sort_dir,
        })


class TaskDetailView(View):
    def get(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        field_values = task.field_values.select_related('field_definition').all()
        dependencies = task.dependencies.select_related('assignee').all()
        return render(request, 'onboarding/task_detail.html', {
            'process': process,
            'task': task,
            'field_values': field_values,
            'dependencies': dependencies,
        })


class TaskCompleteView(View):
    def post(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)

        current_user = None
        user_id = request.session.get('current_user_id')
        if user_id:
            try:
                current_user = SystemUser.objects.get(id=user_id)
            except SystemUser.DoesNotExist:
                pass

        complete_task(task, current_user)
        messages.success(request, f'Opgaven "{task.name}" er markeret som færdig.')

        if request.htmx:
            tasks = _get_tasks_with_overview(process)
            return render(request, 'onboarding/partials/_task_list.html', {
                'process': process,
                'tasks': tasks,
            })
        return redirect('onboarding:detail', pk=process.pk)


class TaskSkipView(View):
    def post(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)

        current_user = None
        user_id = request.session.get('current_user_id')
        if user_id:
            try:
                current_user = SystemUser.objects.get(id=user_id)
            except SystemUser.DoesNotExist:
                pass

        skip_task(task, current_user)
        messages.success(request, f'Opgaven "{task.name}" er sprunget over.')

        if request.htmx:
            tasks = _get_tasks_with_overview(process)
            return render(request, 'onboarding/partials/_task_list.html', {
                'process': process,
                'tasks': tasks,
            })
        return redirect('onboarding:detail', pk=process.pk)


class TaskStartView(View):
    def post(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        start_task(task)

        if request.htmx:
            tasks = _get_tasks_with_overview(process)
            return render(request, 'onboarding/partials/_task_list.html', {
                'process': process,
                'tasks': tasks,
            })
        return redirect('onboarding:detail', pk=process.pk)


class TaskEditView(View):
    def get(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        form = TaskEditForm(initial={
            'assignee': task.assignee,
            'deadline': task.deadline,
        })
        field_values = task.field_values.select_related('field_definition').all()
        return render(request, 'onboarding/task_edit.html', {
            'process': process,
            'task': task,
            'form': form,
            'field_values': field_values,
        })

    def post(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        form = TaskEditForm(request.POST)

        if form.is_valid():
            task.assignee = form.cleaned_data['assignee']
            new_deadline = form.cleaned_data['deadline']
            if new_deadline and new_deadline != task.deadline:
                task.deadline = new_deadline
                task.deadline_overridden = True
            task.save()

            # Update custom field values
            for fv in task.field_values.select_related('field_definition').all():
                field_key = f'field_{fv.field_definition.id}'
                if fv.field_definition.field_type == 'todolist':
                    # Todolist fields are managed via AJAX on the detail page
                    continue
                elif fv.field_definition.field_type == 'checkbox':
                    fv.value_checkbox = field_key in request.POST
                    fv.save(update_fields=['value_checkbox'])
                elif fv.field_definition.field_type == 'number':
                    val = request.POST.get(field_key, '')
                    fv.value_number = float(val) if val else None
                    fv.save(update_fields=['value_number'])
                else:
                    fv.value_text = request.POST.get(field_key, '')
                    fv.save(update_fields=['value_text'])

            messages.success(request, f'Opgaven "{task.name}" er opdateret.')
            return redirect('onboarding:task_detail', pk=process.pk, task_pk=task.pk)

        field_values = task.field_values.select_related('field_definition').all()
        return render(request, 'onboarding/task_edit.html', {
            'process': process,
            'task': task,
            'form': form,
            'field_values': field_values,
        })


class TaskChangeStatusView(View):
    def post(self, request, pk, task_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        new_status = request.POST.get('status', '')

        if new_status not in [s.value for s in TaskStatus]:
            messages.error(request, 'Ugyldig status.')
            return redirect('onboarding:task_detail', pk=process.pk, task_pk=task.pk)

        current_user = None
        user_id = request.session.get('current_user_id')
        if user_id:
            try:
                current_user = SystemUser.objects.get(id=user_id)
            except SystemUser.DoesNotExist:
                pass

        change_task_status(task, new_status, current_user)
        messages.success(request, f'Status for "{task.name}" er ændret til {task.get_status_display()}.')
        return redirect('onboarding:task_detail', pk=process.pk, task_pk=task.pk)


class TaskTodoToggleView(View):
    """AJAX endpoint to toggle a todo item or add a new one in a todolist field."""

    def post(self, request, pk, task_pk, fv_pk):
        process = get_object_or_404(OnboardingProcess, pk=pk)
        task = get_object_or_404(OnboardingTask, pk=task_pk, onboarding=process)
        fv = get_object_or_404(OnboardingTaskFieldValue, pk=fv_pk, task=task)

        if fv.field_definition.field_type != 'todolist':
            return JsonResponse({'error': 'Not a todolist field'}, status=400)

        try:
            data = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        action = data.get('action', '')

        # Parse existing items
        try:
            items = json.loads(fv.value_text) if fv.value_text else []
        except (json.JSONDecodeError, ValueError):
            items = []

        if action == 'toggle':
            index = data.get('index')
            if isinstance(index, int) and 0 <= index < len(items):
                items[index]['done'] = not items[index].get('done', False)
        elif action == 'add':
            text = data.get('text', '').strip()
            if text:
                items.append({'text': text, 'done': False})
        elif action == 'remove':
            index = data.get('index')
            if isinstance(index, int) and 0 <= index < len(items):
                items.pop(index)

        fv.value_text = json.dumps(items, ensure_ascii=False)
        fv.save(update_fields=['value_text'])

        return JsonResponse({'status': 'ok', 'items': items})
