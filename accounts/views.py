from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages

from .models import User
from projects.models import Project
from tasks.models import Task
from activity.models import ActivityLog


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
    if request.user.role == 'ADMIN':
        return redirect('admin_dashboard')
    if request.user.role == 'PROJECT_MANAGER':
        return redirect('project_list')
    return redirect('my_tasks')


@login_required
def admin_dashboard(request):
    if request.user.role != 'ADMIN':
        raise PermissionDenied
    context = {
        'total_users': User.objects.count(),
        'total_projects': Project.objects.count(),
        'total_tasks': Task.objects.count(),
        'completed_tasks': Task.objects.filter(status='COMPLETED').count(),
        'recent_activity': ActivityLog.objects.select_related('actor')[:10],
    }
    return render(request, 'accounts/admin_dashboard.html', context)


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