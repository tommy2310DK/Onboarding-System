from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View

from apps.core.models import SystemUser
from apps.onboarding.models import OnboardingProcess, OnboardingTask, TaskStatus
from .forms import SystemUserForm


class DashboardView(View):
    def get(self, request):
        context = {}
        user_id = request.session.get('current_user_id')
        if user_id:
            try:
                user = SystemUser.objects.get(id=user_id, is_active=True)
                context['user'] = user

                # My tasks (assigned to current user, not completed)
                my_tasks = (
                    OnboardingTask.objects
                    .filter(assignee=user)
                    .exclude(status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED])
                    .select_related('onboarding')
                    .order_by('deadline', 'sort_order')[:10]
                )
                context['my_tasks'] = my_tasks
                context['my_tasks_count'] = my_tasks.count()

                # Overdue tasks for current user
                today = timezone.now().date()
                overdue_count = (
                    OnboardingTask.objects
                    .filter(
                        assignee=user,
                        deadline__lt=today,
                    )
                    .exclude(status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED])
                    .count()
                )
                context['overdue_tasks_count'] = overdue_count

                # Active onboardings (not 100% complete)
                all_processes = OnboardingProcess.objects.prefetch_related('tasks').order_by('-start_date')[:20]
                active_processes = [p for p in all_processes if not p.is_complete]
                context['active_processes'] = active_processes[:5]
                context['active_processes_count'] = len(active_processes)

            except SystemUser.DoesNotExist:
                pass
        return render(request, 'core/dashboard.html', context)


class SwitchUserView(View):
    def post(self, request):
        user_id = request.POST.get('user_id')
        if user_id:
            try:
                user = SystemUser.objects.get(id=user_id, is_active=True)
                request.session['current_user_id'] = user.id
            except SystemUser.DoesNotExist:
                request.session.pop('current_user_id', None)
        else:
            request.session.pop('current_user_id', None)
        return redirect(request.POST.get('next', '/'))


# --- User Administration ---

class UserListView(View):
    def get(self, request):
        query = request.GET.get('q', '')
        show_inactive = request.GET.get('inactive', '') == '1'
        users = SystemUser.objects.all()
        if not show_inactive:
            users = users.filter(is_active=True)
        if query:
            users = (
                users.filter(name__icontains=query) |
                users.filter(email__icontains=query) |
                users.filter(department__icontains=query)
            ).distinct()
        return render(request, 'core/user_list.html', {
            'users': users,
            'query': query,
            'show_inactive': show_inactive,
        })


class UserCreateView(View):
    def get(self, request):
        form = SystemUserForm()
        return render(request, 'core/user_form.html', {
            'form': form,
            'is_create': True,
        })

    def post(self, request):
        form = SystemUserForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f'Brugeren "{user.name}" er oprettet.')
            return redirect('core:user_detail', pk=user.pk)
        return render(request, 'core/user_form.html', {
            'form': form,
            'is_create': True,
        })


class UserDetailView(View):
    def get(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        # Tasks assigned to this user
        assigned_tasks = (
            OnboardingTask.objects
            .filter(assignee=user)
            .exclude(status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED])
            .select_related('onboarding')
            .order_by('deadline')[:10]
        )
        completed_count = OnboardingTask.objects.filter(
            assignee=user, status=TaskStatus.COMPLETED
        ).count()
        return render(request, 'core/user_detail.html', {
            'user_obj': user,
            'assigned_tasks': assigned_tasks,
            'completed_count': completed_count,
        })


class UserUpdateView(View):
    def get(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        form = SystemUserForm(instance=user)
        return render(request, 'core/user_form.html', {
            'form': form,
            'user_obj': user,
            'is_create': False,
        })

    def post(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        form = SystemUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'Brugeren "{user.name}" er opdateret.')
            return redirect('core:user_detail', pk=user.pk)
        return render(request, 'core/user_form.html', {
            'form': form,
            'user_obj': user,
            'is_create': False,
        })


class UserToggleActiveView(View):
    def post(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        status = 'aktiveret' if user.is_active else 'deaktiveret'
        messages.success(request, f'Brugeren "{user.name}" er {status}.')
        return redirect('core:user_detail', pk=user.pk)


class UserDeleteView(View):
    def get(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        # Count related data for the confirmation page
        active_tasks_count = OnboardingTask.objects.filter(
            assignee=user
        ).exclude(status__in=[TaskStatus.COMPLETED, TaskStatus.SKIPPED]).count()
        all_tasks_count = OnboardingTask.objects.filter(assignee=user).count()
        created_onboardings_count = OnboardingProcess.objects.filter(created_by=user).count()
        return render(request, 'core/user_confirm_delete.html', {
            'user_obj': user,
            'active_tasks_count': active_tasks_count,
            'all_tasks_count': all_tasks_count,
            'created_onboardings_count': created_onboardings_count,
        })

    def post(self, request, pk):
        user = get_object_or_404(SystemUser, pk=pk)
        name = user.name
        # Clear session if deleting the current user
        if request.session.get('current_user_id') == user.pk:
            request.session.pop('current_user_id', None)
        user.delete()
        messages.success(request, f'Brugeren "{name}" er slettet.')
        return redirect('core:user_list')
