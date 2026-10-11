from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required

from accounts.models import User
from activity.models import ActivityLog
from .models import Project, ProjectMember
from .permissions import can_access_project, can_manage_project, user_projects


@login_required
def project_list(request):
    projects = user_projects(request.user)
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_access_project(request.user, project):
        raise Http404
    context = {
        'project': project,
        'members': project.memberships.select_related('user'),
        'tasks': project.tasks.all(),
        'developers': User.objects.filter(role='DEVELOPER', is_active=True),
    }
    return render(request, 'projects/project_detail.html', context)


@login_required
def project_create(request):
    if request.user.role not in ('PROJECT_MANAGER', 'ADMIN'):
        raise PermissionDenied
    if request.method == 'POST':
        project = Project.objects.create(
            name=request.POST.get('name'),
            description=request.POST.get('description', ''),
            manager=request.user,
            start_date=request.POST.get('start_date'),
            deadline=request.POST.get('deadline'),
            status=request.POST.get('status', 'PLANNED'),
            priority=request.POST.get('priority', 'MEDIUM'),
        )
        ProjectMember.objects.create(project=project, user=request.user, added_by=request.user)
        ActivityLog.log(request.user, 'PROJECT_CREATED', f'Created project "{project.name}"', project=project)
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'project': None})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise Http404
    if request.method == 'POST':
        project.name = request.POST.get('name')
        project.description = request.POST.get('description', '')
        project.start_date = request.POST.get('start_date')
        project.deadline = request.POST.get('deadline')
        project.status = request.POST.get('status')
        project.priority = request.POST.get('priority')
        project.save()
        ActivityLog.log(request.user, 'PROJECT_UPDATED', f'Updated project "{project.name}"', project=project)
        return redirect('project_detail', pk=project.pk)
    return render(request, 'projects/project_form.html', {'project': project})


@login_required
def project_archive(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise Http404
    project.is_archived = not project.is_archived
    project.save()
    return redirect('project_list')


@login_required
def member_add(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise Http404
    if request.method == 'POST':
        user = get_object_or_404(User, pk=request.POST.get('user_id'), role='DEVELOPER')
        member, created = ProjectMember.objects.get_or_create(project=project, user=user, defaults={'added_by': request.user})
        if created:
            ActivityLog.log(request.user, 'MEMBER_ADDED', f'Added {user.email} to project', project=project)
    return redirect('project_detail', pk=pk)


@login_required
def member_remove(request, pk, user_id):
    project = get_object_or_404(Project, pk=pk)
    if not can_manage_project(request.user, project):
        raise Http404
    ProjectMember.objects.filter(project=project, user_id=user_id).delete()
    ActivityLog.log(request.user, 'MEMBER_REMOVED', 'Removed a member from project', project=project)
    return redirect('project_detail', pk=pk)