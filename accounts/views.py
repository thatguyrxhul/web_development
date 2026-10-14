from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.db.models import Count, Q
from datetime import timedelta
from django.utils import timezone
from projects.models import Project
from tasks.models import Task
from activity.models import ActivityLog
from .models import User


def login_view(request):
    if request.method == 'POST':
        user = authenticate(request, email=request.POST.get('email'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Invalid email or password')
    return render(request, 'accounts/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home(request):
    user = request.user
    def annotated(qs):
        return qs.annotate(
            total_tasks=Count('tasks', distinct=True),
            done_tasks=Count('tasks', filter=Q(tasks__status='COMPLETED'), distinct=True),
        )
    if user.role == 'DEVELOPER':
        projects = annotated(Project.objects.filter(memberships__user=user).distinct())
        my_tasks = Task.objects.filter(assignee=user).select_related('project')
    elif user.role == 'PROJECT_MANAGER':
        projects = annotated(Project.objects.filter(manager=user))
        my_tasks = Task.objects.filter(project__manager=user).select_related('project')
    else:
        projects = annotated(Project.objects.all())
        my_tasks = Task.objects.all().select_related('project')
    completed = my_tasks.filter(status='COMPLETED').count()
    created = list(my_tasks.order_by('created_at').values_list('created_at', flat=True))
    done_qs = list(my_tasks.filter(status='COMPLETED').order_by('created_at'))
    comp = {t.id: t.created_at for t in done_qs}
    if comp:
        for k, v in ActivityLog.objects.filter(
            task_id__in=comp, action='TASK_STATUS_CHANGED', new_value='COMPLETED'
        ).order_by('timestamp').values_list('task_id', 'timestamp'):
            comp[k] = v
    done_times = sorted(comp.values())

    today = timezone.localdate()
    days = [today - timedelta(days=9 - i) for i in range(10)]

    def series(times):
        counts = {}
        for t in times:
            d = t.date()
            counts[d] = counts.get(d, 0) + 1
        run = sum(1 for t in times if t.date() < days[0])
        vals = []
        for d in days:
            run += counts.get(d, 0)
            vals.append(run)
        return [d.strftime('%b %d') for d in days], vals

    chart_labels, chart_vals = series(created)
    done_labels, done_vals = series(done_times)

    context = {
        'open_tasks': my_tasks.count() - completed,
        'completed_tasks': completed,
        'active_projects': projects.filter(is_archived=False).count(),
        'total_projects': projects.count(),
        'projects': projects[:6],
        'tasks': my_tasks.exclude(status='COMPLETED')[:6],
        'is_dev': user.role == 'DEVELOPER',
        'chart_labels': chart_labels,
        'chart_vals': chart_vals,
        'done_labels': done_labels,
        'done_vals': done_vals,
    }
    return render(request, 'accounts/dashboard.html', context)




@login_required
def user_list(request):
    if request.user.role != 'ADMIN':
        raise PermissionDenied
    users = User.objects.all().order_by('role', 'email')
    return render(request, 'accounts/user_list.html', {'users': users})


@login_required
def user_toggle(request, pk):
    if request.user.role != 'ADMIN':
        raise PermissionDenied
    user = get_object_or_404(User, pk=pk)
    if user != request.user:
        user.is_active = not user.is_active
        user.save()
    return redirect('user_list')


@login_required
def user_create(request):
    if request.user.role != 'ADMIN':
        raise PermissionDenied
    if request.method == 'POST':
        email = request.POST.get('email')
        role = request.POST.get('role')
        if role not in ('ADMIN', 'PROJECT_MANAGER', 'DEVELOPER'):
            role = 'DEVELOPER'   # never trust client input blindly
        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists')
        else:
            User.objects.create_user(
                username=request.POST.get('username') or email.split('@')[0],
                email=email,
                password=request.POST.get('password'),
                first_name=request.POST.get('first_name', ''),
                last_name=request.POST.get('last_name', ''),
                role=role,
            )
            messages.success(request, f'User {email} created')
            return redirect('user_list')
    return render(request, 'accounts/user_create.html')