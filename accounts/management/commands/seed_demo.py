from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from activity.models import ActivityLog
from projects.models import Project, ProjectMember
from tasks.models import Comment, Label, Task


class Command(BaseCommand):
    help = 'Seed demo users, projects, tasks, comments and activity (idempotent - safe to re-run).'

    def handle(self, *args, **options):
        now = timezone.now()

        def ago(days):
            return now - timedelta(days=days)

        # --- Users -------------------------------------------------------
        def ensure_user(username, email, password, role, first, last):
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    'username': username,
                    'role': role,
                    'first_name': first,
                    'last_name': last,
                },
            )
            if created:
                user.set_password(password)
                user.save()
            return user

        rahul = ensure_user('rahul', 'rahul@gmail.com', 'rahul@123', 'ADMIN', 'Rahul', 'Sharma')
        martin = ensure_user('martin', 'martin@test.com', 'martin@123', 'PROJECT_MANAGER', 'Martin', 'Rao')
        priya = ensure_user('priya', 'priya@test.com', 'priya@123', 'PROJECT_MANAGER', 'Priya', 'Nair')
        arjun = ensure_user('arjun', 'arjun@test.com', 'arjun@123', 'DEVELOPER', 'Arjun', 'Mehta')
        sneha = ensure_user('sneha', 'sneha@test.com', 'sneha@123', 'DEVELOPER', 'Sneha', 'Iyer')

        # --- Labels (the 6 required by the brief) ------------------------
        labels = {}
        for name, color in [('Bug', '#ef4444'), ('Feature', '#10b981'), ('UI', '#3b82f6'),
                            ('Backend', '#8b5cf6'), ('Database', '#f59e0b'), ('Security', '#64748b')]:
            label, _ = Label.objects.get_or_create(name=name, defaults={'color': color})
            labels[name] = label

        # --- Projects & members ------------------------------------------
        p1, _ = Project.objects.get_or_create(
            name='DevBoard Platform',
            defaults={
                'description': 'Internal kanban platform for planning and tracking engineering work.',
                'manager': martin,
                'start_date': date(2026, 9, 1),
                'deadline': date(2026, 11, 30),
                'status': 'IN_PROGRESS',
                'priority': 'HIGH',
            },
        )
        p2, _ = Project.objects.get_or_create(
            name='Client Portal Redesign',
            defaults={
                'description': 'Rebuild of the customer-facing portal on the new design system.',
                'manager': priya,
                'start_date': date(2026, 10, 1),
                'deadline': date(2026, 12, 15),
                'status': 'PLANNED',
                'priority': 'MEDIUM',
            },
        )
        for project, member, added_by in [(p1, arjun, martin), (p1, sneha, martin), (p2, arjun, priya)]:
            ProjectMember.objects.get_or_create(project=project, user=member,
                                                defaults={'added_by': added_by})

        # --- Tasks (11, backdated so charts and ordering look real) -------
        def ensure_task(project, title, status, priority, assignee, description='',
                        deadline=None, age=0):
            task, _ = Task.objects.get_or_create(
                project=project,
                title=title,
                defaults={
                    'description': description,
                    'status': status,
                    'priority': priority,
                    'assignee': assignee,
                    'deadline': deadline,
                    'created_by': project.manager,
                },
            )
            Task.objects.filter(pk=task.pk).update(created_at=ago(age), updated_at=ago(age))
            return task

        tasks = [
            ensure_task(p1, 'Design database schema', 'COMPLETED', 'HIGH', arjun,
                        'ER diagram, models and migration plan for the first release.', age=40),
            ensure_task(p1, 'Build authentication views', 'COMPLETED', 'HIGH', sneha,
                        'Email login, logout, password validators and role routing.', age=38),
            ensure_task(p1, 'Implement project permissions layer', 'IN_REVIEW', 'CRITICAL', arjun,
                        'can_access / can_manage / can_edit helpers shared by every view.',
                        date(2026, 10, 16), age=30),
            ensure_task(p1, 'Create kanban board UI', 'IN_PROGRESS', 'HIGH', sneha,
                        'Four-column board with status buttons and column counts.', age=21),
            ensure_task(p1, 'Write activity feed API', 'IN_PROGRESS', 'MEDIUM', arjun,
                        'Project-scoped activity stream with actor and timestamp.', age=14),
            ensure_task(p1, 'Set up CI pipeline', 'TODO', 'MEDIUM', sneha,
                        'Lint + test runner on every push.', date(2026, 10, 10), age=10),
            ensure_task(p1, 'Draft user documentation', 'TODO', 'LOW', None,
                        'README walkthrough, screenshots and FAQ.', age=6),
            ensure_task(p2, 'Wireframe dashboard screens', 'COMPLETED', 'MEDIUM', arjun,
                        'Low-fidelity flows for login, dashboard and project views.', age=12),
            ensure_task(p2, 'Implement responsive navigation', 'IN_REVIEW', 'HIGH', arjun,
                        'Collapsible sidebar and mobile top bar.', age=8),
            ensure_task(p2, 'Integrate billing API', 'TODO', 'CRITICAL', arjun,
                        'Subscription states and invoice history endpoints.', date(2026, 10, 20), age=4),
            ensure_task(p2, 'QA regression pass', 'TODO', 'MEDIUM', None,
                        'Cross-browser checks before the pilot release.', date(2026, 11, 1), age=2),
        ]

        # --- Labels on tasks (mapped to the required label set) -----------
        task_labels = [
            ['Backend', 'Database'],
            ['Backend', 'Security'],
            ['Backend', 'Security'],
            ['UI', 'Feature'],
            ['Backend'],
            ['Feature'],
            ['UI'],
            ['UI'],
            ['UI'],
            ['Backend', 'Bug'],
            ['Bug'],
        ]
        for task, names in zip(tasks, task_labels):
            for name in names:
                task.labels.add(labels[name])

        # --- Comments -----------------------------------------------------
        comment_specs = [
            (tasks[2], martin, 'Looks solid. Please tighten the 404 branch and we can merge.', 3),
            (tasks[2], arjun, 'Done - also added a regression test for the denial path.', 2),
            (tasks[3], sneha, 'Columns render correctly, polishing the counts next.', 1),
        ]
        for task, author, body, days in comment_specs:
            comment, _ = Comment.objects.get_or_create(task=task, author=author, body=body)
            Comment.objects.filter(pk=comment.pk).update(created_at=ago(days), updated_at=ago(days))

        # --- Activity feed (backdated) ------------------------------------
        activity_specs = [
            (martin, 'PROJECT_CREATED', 'Created project "DevBoard Platform"', p1, None, '', '', 42),
            (martin, 'MEMBER_ADDED', 'Added Arjun Mehta to DevBoard Platform', p1, None, '', '', 40),
            (priya, 'PROJECT_CREATED', 'Created project "Client Portal Redesign"', p2, None, '', '', 13),
            (arjun, 'TASK_STATUS_CHANGED',
             'Implement project permissions layer: IN_PROGRESS -> IN_REVIEW',
             p1, tasks[2], 'IN_PROGRESS', 'IN_REVIEW', 2),
            (sneha, 'COMMENT_ADDED', 'Commented on "Create kanban board UI"', p1, tasks[3], '', '', 1),
        ]
        for actor, action, description, project, task, old, new, days in activity_specs:
            entry, _ = ActivityLog.objects.get_or_create(
                actor=actor, action=action, description=description,
                project=project, task=task, old_value=old, new_value=new,
            )
            ActivityLog.objects.filter(pk=entry.pk).update(timestamp=ago(days))

        self.stdout.write(self.style.SUCCESS(
            'Seeded 5 users, 2 projects, 11 tasks, '
            f'{Comment.objects.count()} comments, {ActivityLog.objects.count()} activity entries.'))