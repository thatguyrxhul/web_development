from django.contrib import admin
from .models import Project, ProjectMember

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'manager', 'status', 'priority', 'deadline', 'is_archived')
    list_filter = ('status', 'priority', 'is_archived')
    search_fields = ('name',)

@admin.register(ProjectMember)
class ProjectMemberAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'joined_at')
    list_filter = ('project',)