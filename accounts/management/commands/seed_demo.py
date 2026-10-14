from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from activity.models import ActivityLog
from projects.models import Project, ProjectMember
from tasks.models import Comment, Label, Task


class Command(BaseCommand):
    help = 'Seed the database with demo users, projects, tasks, comments and activity.'

    def handle(self, *args, **options):
        if User.objects.filter(email='rahul@gmail.com').exists():
            self.stdout.write(self.style.WARNING('Demo data already present - seed skipped.'))
            return

        now = timezone.now()

        def ago(days, hours=0):
            return now - timedelta(days=days, hours=hours)

        # --- Users ---
        rahul = User.objects.create_user('rahul', 'rahul@gmail.com', 'rahul@123',
                                         role='ADMIN', first_name='Rahul', last_name='Sharma')
        martin = User.objects.create_user('martin', 'martin@test.com', 'martin@123',
                                          role='PROJECT_MANAGER', first_name='Martin', last_name='Rao')
        priya = User.objects.create_user('priya', 'priya@test.com', 'priya@123',
                                         role='PROJECT_MANAGER', first_name='Priya', last_name='Nair')
        arjun = User.objects.create_user('arjun', 'arjun@test.com', 'arjun@123',
                                         role='DEVELOPER', first_name='Arjun', last_name='Mehta')
        sneha = User.objects.create_user('sneha', 'sneha@test.com', 'sneha@123',
                                         role='DEVELOPER', first_name='Sneha', last_name='Iyer')

        # --- Labels ---
        labels = {}
        for name, color in [('Frontend', '#3b82f6'), ('Backend', '#8b5cf6'), ('Bug', '#ef4444'),
                            ('Feature', '#10b981'), ('Design', '#f59e0b'), ('DevOps', '#64748b')]:
            labels[name] = Label.objects.create(name=name, color=color)

        # --- Projects & members ---
        p1 = Project.objects.create(
            name='DevBoard Platform',
            description='Internal kanban platform for planning and tracking engineering work.',
            manager=martin, start_date='2026-09-01', deadline='2026-11-30',
            status='IN_PROGRESS', priority='HIGH')
        p2 = Project.objects.create(
            name='Client Portal Redesign',
            description='Rebuild of the customer-facing portal on the new design system.',
            manager=priya, start_date='2026-10-01', deadline='2026-12-15',
            status='PLANNED', priority='MEDIUM')
        ProjectMember.objects.create(project=p1, user=arjun, added_by=martin)
        ProjectMember.objects.create(project=p1, user=sneha, added_by=martin)
        ProjectMember.objects.create(project=p2, user=arjun, added_by=priya)

        # --- Tasks (11) ---
        def make_task(project, title, status, priority, assignee, description='', deadline=None):
            return Task.objects.create(
                title=title, description=description, project=project, assignee=assignee,
                status=status, priority=priority, deadline=deadline, created_by=project.manager)

        tasks = [
            make_task(p1, 'Design database schema', 'COMPLETED', 'HIGH', arjun,
                      'ER diagram, models and migration plan for the first release.'),
            make_task(p1, 'Build authentication views', 'COMPLETED', 'HIGH', sneha,
                      'Email login, logout, password validators and role routing.'),
            make_task(p1, 'Implement project permissions layer', 'IN_REVIEW', 'CRITICAL', arjun,
                      'can_access / can_manage / can_edit helpers shared by every view.',
                      '2026-10-16'),
            make_task(p1, 'Create kanban board UI', 'IN_PROGRESS', 'HIGH', sneha,
                      'Four-column board with status buttons and column counts.'),
            make_task(p1, 'Write activity feed API', 'IN_PROGRESS', 'MEDIUM', arjun,
                      'Project-scoped activity stream with actor and timestamp.'),
            make_task(p1, 'Set up CI pipeline', 'TODO', 'MEDIUM', sneha,
                      'Lint + test runner on every push.', '2026-10-10'),
            make_task(p1, 'Draft user documentation', 'TODO', 'LOW', None,
                      'README walkthrough, screenshots and FAQ.'),
            make_task(p2, 'Wireframe dashboard screens', 'COMPLETED', 'MEDIUM', arjun,
                      'Low-fidelity flows for login, dashboard and project views.'),
            make_task(p2, 'Implement responsive navigation', 'IN_REVIEW', 'HIGH', arjun,
                      'Collapsible sidebar and mobile top bar.'),
            make_task(p2, 'Integrate billing API', 'TODO', 'CRITICAL', arjun,
                      'Subscription states and invoice history endpoints.', '2026-10-20'),
            make_task(p2, 'QA regression pass', 'TODO', 'MEDIUM', None,
                      'Cross-browser checks before the pilot release.', '2026-11-01'),
        ]

        # Age the tasks so ordering and dashboard charts look real
        for task, days in zip(tasks, [40, 38, 30, 21, 14, 10, 6, 12, 8, 4, 2]):
            Task.objects.filter(pk=task.pk).update(created_at=ago(days), updated_at=ago(days))

        # --- Labels on tasks ---
        tasks[0].labels.add(labels['Backend'], labels['Design'])
        tasks[1].labels.add(labels['Backend'])
        tasks[2].labels.add(labels['Backend'], labels['Feature'])
        tasks[3].labels.add(labels['Frontend'], labels['Feature'])
        tasks[4].labels.add(labels['Backend'])
        tasks[5].labels.add(labels['DevOps'], labels['Bug'])
        tasks[6].labels.add(labels['Design'])
        tasks[7].labels.add(labels['Design'])
        tasks[8].labels.add(labels['Frontend'])
        tasks[9].labels.add(labels['Backend'], labels['Bug'])
        tasks[10].labels.add(labels['Feature'])

        # --- Comments ---
        comments = [
            Comment.objects.create(task=tasks[2], author=martin,
                                   body='Looks solid. Please tighten the 404 branch and we can merge.'),
            Comment.objects.create(task=tasks[2], author=arjun,
                                   body='Done - also added a regression test for the denial path.'),
            Comment.objects.create(task=tasks[3], author=sneha,
                                   body='Columns render correctly, polishing the counts next.'),
        ]
        for comment, days in zip(comments, [3, 2, 1]):
            Comment.objects.filter(pk=comment.pk).update(created_at=ago(days), updated_at=ago(days))

        # --- Activity feed (backdated) ---
        entries = [
            (ActivityLog.log(martin, 'PROJECT_CREATED', 'Created project "DevBoard Platform"', project=p1), 42),
            (ActivityLog.log(martin, 'MEMBER_ADDED', 'Added Arjun Mehta to DevBoard Platform', project=p1), 40),
            (ActivityLog.log(priya, 'PROJECT_CREATED', 'Created project "Client Portal Redesign"', project=p2), 13),
            (ActivityLog.log(arjun, 'TASK_STATUS_CHANGED',
                             'Implement project permissions layer: IN_PROGRESS -> IN_REVIEW',
                             project=p1, task=tasks[2], old='IN_PROGRESS', new='IN_REVIEW'), 2),
            (ActivityLog.log(sneha, 'COMMENT_ADDED', 'Commented on "Create kanban board UI"',
                             project=p1, task=tasks[3]), 1),
        ]
        for entry, days in entries:
            ActivityLog.objects.filter(pk=entry.pk).update(timestamp=ago(days))

        self.stdout.write(self.style.SUCCESS(
            'Seeded 5 users, 2 projects, 11 tasks, '
            f'{Comment.objects.count()} comments, {ActivityLog.objects.count()} activity entries.'))