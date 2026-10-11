from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.contrib.auth.decorators import login_required

from projects.models import Project
from projects.permissions import can_access_project
from .models import ActivityLog


@login_required
def project_activity(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not can_access_project(request.user, project):
        raise Http404
    logs = ActivityLog.objects.filter(project=project).select_related('actor')[:50]
    return render(request, 'activity/project_activity.html', {'project': project, 'logs': logs})