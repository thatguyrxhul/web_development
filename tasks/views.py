from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, FileResponse
from django.http import JsonResponse
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone

from accounts.models import User
from projects.models import Project
from projects.permissions import can_access_project, can_manage_project, can_edit_task
from activity.models import ActivityLog
from .models import Task, Comment, Attachment, Label, TaskLabel

VALID_NEXT = {'TODO': 'IN_PROGRESS', 'IN_PROGRESS': 'IN_REVIEW', 'IN_REVIEW': 'COMPLETED'}


@login_required
def my_tasks(request):
    tasks = Task.objects.filter(assignee=request.user).select_related('project')
    context = {
        'tasks': tasks,
        'assigned': tasks.count(),
        'completed': tasks.filter(status='COMPLETED').count(),
        'overdue': tasks.filter(deadline__lt=timezone.now().date()).exclude(status='COMPLETED').count(),
    }
    return render(request, 'tasks/my_tasks.html', context)


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task.objects.select_related('project', 'assignee'), pk=pk)
    if not can_access_project(request.user, task.project):
        raise Http404
    context = {
        'task': task,
        'comments': task.comments.select_related('author'),
        'attachments': task.attachments.all(),
        'labels': Label.objects.all(),
        'can_edit': can_edit_task(request.user, task),
    }
    return render(request, 'tasks/task_detail.html', context)


@login_required
def task_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_manage_project(request.user, project):
        raise Http404
    if request.method == 'POST':
        assignee = None
        if request.POST.get('assignee'):
            assignee = get_object_or_404(User, pk=request.POST['assignee'], project_memberships__project=project)
        task = Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description', ''),
            project=project,
            assignee=assignee,
            priority=request.POST.get('priority', 'MEDIUM'),
            deadline=request.POST.get('deadline') or None,
            created_by=request.user,
        )
        for label_id in request.POST.getlist('labels'):
            TaskLabel.objects.get_or_create(task=task, label_id=label_id)
        ActivityLog.log(request.user, 'TASK_CREATED', f'Created task "{task.title}"', project=project, task=task)
        return redirect('task_detail', pk=task.pk)
    context = {
        'project': project,
        'members': project.memberships.select_related('user'),
        'labels': Label.objects.all(),
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task.objects.select_related('project'), pk=pk)
    if not can_manage_project(request.user, task.project):
        raise Http404
    if request.method == 'POST':
        if request.POST.get('assignee'):
            assignee = get_object_or_404(User, pk=request.POST['assignee'], project_memberships__project=task.project)
        else:
            assignee = None
        if task.assignee_id != assignee.id if assignee else (task.assignee_id is not None):
            ActivityLog.log(request.user, 'TASK_ASSIGNED', f'Reassigned "{task.title}"', project=task.project, task=task)
        if task.priority != request.POST.get('priority'):
            ActivityLog.log(request.user, 'TASK_PRIORITY_CHANGED', f'Priority of "{task.title}" changed',
                            project=task.project, task=task, old=task.priority, new=request.POST.get('priority'))
        task.title = request.POST.get('title')
        task.description = request.POST.get('description', '')
        task.assignee = assignee
        task.priority = request.POST.get('priority')
        task.deadline = request.POST.get('deadline') or None
        task.save()
        for label_id in request.POST.getlist('labels'):
            TaskLabel.objects.get_or_create(task=task, label_id=label_id)
        return redirect('task_detail', pk=task.pk)
    context = {
        'task': task,
        'members': task.project.memberships.select_related('user'),
        'labels': Label.objects.all(),
    }
    return render(request, 'tasks/task_form.html', context)


@login_required
def task_status(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_edit_task(request.user, task):
        raise Http404
    if request.method == 'POST':
        new_status = request.POST.get('status')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if new_status != VALID_NEXT.get(task.status):
            error = f'Invalid transition: {task.status} -> {new_status}'
            messages.error(request, error)
            if is_ajax:
                return JsonResponse({'ok': False, 'error': error}, status=400)
        else:
            old = task.status
            task.status = new_status
            task.save()
            ActivityLog.log(request.user, 'TASK_STATUS_CHANGED', f'{task.title}: {old} -> {new_status}',
                            project=task.project, task=task, old=old, new=new_status)
            if is_ajax:
                return JsonResponse({'ok': True})
    return redirect('task_detail', pk=pk)


STATUS_LABELS = {'TODO': 'Todo', 'IN_PROGRESS': 'In Progress', 'IN_REVIEW': 'In Review', 'COMPLETED': 'Completed'}


@login_required
def kanban(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not can_access_project(request.user, project):
        raise Http404
    tasks = project.tasks.all()
    columns = [(s, STATUS_LABELS[s], tasks.filter(status=s))
               for s in ['TODO', 'IN_PROGRESS', 'IN_REVIEW', 'COMPLETED']]
    return render(request, 'tasks/kanban.html', {'project': project, 'columns': columns})


@login_required
def comment_add(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_access_project(request.user, task.project):
        raise Http404
    if request.method == 'POST' and request.POST.get('body'):
        Comment.objects.create(task=task, author=request.user, body=request.POST['body'])
        ActivityLog.log(request.user, 'COMMENT_ADDED', f'Commented on "{task.title}"', project=task.project, task=task)
    return redirect('task_detail', pk=pk)


@login_required
def attachment_upload(request, pk):
    task = get_object_or_404(Task, pk=pk)
    if not can_access_project(request.user, task.project):
        raise Http404
    if request.method == 'POST' and request.FILES.get('file'):
        Attachment.objects.create(task=task, uploaded_by=request.user, file=request.FILES['file'])
        ActivityLog.log(request.user, 'ATTACHMENT_UPLOADED', f'Uploaded file to "{task.title}"', project=task.project, task=task)
    return redirect('task_detail', pk=pk)


@login_required
def attachment_download(request, pk):
    attachment = get_object_or_404(Attachment, pk=pk)
    if not can_access_project(request.user, attachment.task.project):
        raise Http404
    return FileResponse(attachment.file.open('rb'), as_attachment=True, filename=attachment.file.name.split('/')[-1])


@login_required
def label_list(request):
    if request.user.role not in ('ADMIN', 'PROJECT_MANAGER'):
        raise PermissionDenied
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        color = request.POST.get('color', '#6b7280')
        if name:
            label, created = Label.objects.get_or_create(name=name, defaults={'color': color})
            if created:
                messages.success(request, f'Label "{name}" created')
            else:
                messages.error(request, f'Label "{name}" already exists')
        return redirect('label_list')
    return render(request, 'tasks/label_list.html', {'labels': Label.objects.all().order_by('name')})

@login_required
def label_edit(request, pk):
    if request.user.role not in ('ADMIN', 'PROJECT_MANAGER'):
        raise PermissionDenied
    label = get_object_or_404(Label, pk=pk)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            label.name = name
            label.color = request.POST.get('color', label.color)
            label.save()
            messages.success(request, 'Label updated')
        return redirect('label_list')
    return render(request, 'tasks/label_edit.html', {'label': label})


@login_required
def label_delete(request, pk):
    if request.user.role not in ('ADMIN', 'PROJECT_MANAGER'):
        raise PermissionDenied
    label = get_object_or_404(Label, pk=pk)
    name = label.name
    label.delete()
    messages.success(request, f'Label "{name}" deleted')
    return redirect('label_list')