"""
URL configuration for devboard project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.urls import path
from . import views

urlpatterns = [
    path('my-tasks/', views.my_tasks, name='my_tasks'),
    path('labels/', views.label_list, name='label_list'),
    path('labels/<int:pk>/edit/', views.label_edit, name='label_edit'),
    path('labels/<int:pk>/delete/', views.label_delete, name='label_delete'),
    path('projects/<int:project_pk>/kanban/', views.kanban, name='kanban'),
    path('projects/<int:project_pk>/tasks/create/', views.task_create, name='task_create'),
    path('tasks/<int:pk>/', views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/edit/', views.task_edit, name='task_edit'),
    path('tasks/<int:pk>/status/', views.task_status, name='task_status'),
    path('tasks/<int:pk>/comments/', views.comment_add, name='comment_add'),
    path('tasks/<int:pk>/attachments/', views.attachment_upload, name='attachment_upload'),
    path('attachments/<int:pk>/download/', views.attachment_download, name='attachment_download'),
]