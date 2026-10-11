from django.db.models import Q
from .models import Project


def is_admin(user):
    return user.is_authenticated and user.role == 'ADMIN'


def can_access_project(user, project):
    if not user.is_authenticated:
        return False
    return is_admin(user) or project.manager_id == user.id or project.memberships.filter(user=user).exists()


def can_manage_project(user, project):
    return user.is_authenticated and (is_admin(user) or project.manager_id == user.id)


def can_edit_task(user, task):
    return can_manage_project(user, task.project) or task.assignee_id == user.id


def user_projects(user):
    if is_admin(user):
        return Project.objects.all()
    return Project.objects.filter(Q(manager=user) | Q(memberships__user=user)).distinct()