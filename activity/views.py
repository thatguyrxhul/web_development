from django.shortcuts import render, get_object_or_404
from django.http import Http404, JsonResponse
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from projects.models import Project
from projects.permissions import can_access_project, user_projects
from .models import ActivityLog


@login_required
def project_activity(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_access_project(request.user, project):
        raise Http404
    logs = ActivityLog.objects.filter(project=project).select_related('actor')[:50]
    return render(request, 'activity/project_activity.html', {'project': project, 'logs': logs})


@login_required
def activity_feed(request):
    qs = ActivityLog.objects.select_related('actor', 'project')
    if request.user.role == 'DEVELOPER':
        qs = qs.filter(Q(project__in=user_projects(request.user)) | Q(task__assignee=request.user) | Q(actor=request.user))
    elif request.user.role == 'PROJECT_MANAGER':
        qs = qs.filter(Q(project__in=user_projects(request.user)) | Q(actor=request.user))
    logs = qs[:4]
    return JsonResponse({'items': [{
        'actor': log.actor.display_name if log.actor else 'System',
        'description': log.description,
        'time': log.timestamp.strftime('%b %d, %H:%M'),
    } for log in logs]})