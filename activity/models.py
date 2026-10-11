from django.conf import settings
from django.db import models

from projects.models import Project
from tasks.models import Task


class ActivityLog(models.Model):
    class Action(models.TextChoices):
        PROJECT_CREATED = 'PROJECT_CREATED', 'Project created'
        PROJECT_UPDATED = 'PROJECT_UPDATED', 'Project updated'
        MEMBER_ADDED = 'MEMBER_ADDED', 'Member added'
        MEMBER_REMOVED = 'MEMBER_REMOVED', 'Member removed'
        TASK_CREATED = 'TASK_CREATED', 'Task created'
        TASK_STATUS_CHANGED = 'TASK_STATUS_CHANGED', 'Task status changed'
        TASK_ASSIGNED = 'TASK_ASSIGNED', 'Task assigned'
        TASK_PRIORITY_CHANGED = 'TASK_PRIORITY_CHANGED', 'Task priority changed'
        COMMENT_ADDED = 'COMMENT_ADDED', 'Comment added'
        ATTACHMENT_UPLOADED = 'ATTACHMENT_UPLOADED', 'Attachment uploaded'

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='activities',
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='activity_logs',
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    description = models.CharField(max_length=255)
    old_value = models.CharField(max_length=50, blank=True)
    new_value = models.CharField(max_length=50, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action}: {self.description}"



    @classmethod
    def log(cls, actor, action, description, project=None, task=None, old='', new=''):
        return cls.objects.create(actor=actor, project=project, task=task, action=action,
                                  description=description, old_value=old, new_value=new)