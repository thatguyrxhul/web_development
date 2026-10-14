from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project, ProjectMember
from tasks.models import Task


class WorkflowTests(TestCase):
    """Status must move TODO -> IN_PROGRESS -> IN_REVIEW -> COMPLETED, one step at a time."""

    @classmethod
    def setUpTestData(cls):
        cls.pm = User.objects.create_user('wfp', 'wfp@t.com', 'pw12345!', role='PROJECT_MANAGER')
        cls.dev_a = User.objects.create_user('wfa', 'wfa@t.com', 'pw12345!', role='DEVELOPER')
        cls.dev_b = User.objects.create_user('wfb', 'wfb@t.com', 'pw12345!', role='DEVELOPER')
        cls.project = Project.objects.create(name='Workflow Project', manager=cls.pm,
                                             start_date='2026-10-01', deadline='2026-11-30')
        ProjectMember.objects.create(project=cls.project, user=cls.dev_a)
        ProjectMember.objects.create(project=cls.project, user=cls.dev_b)
        cls.task_todo = Task.objects.create(title='Todo task', project=cls.project,
                                            assignee=cls.dev_a, created_by=cls.pm, status='TODO')
        cls.task_prog = Task.objects.create(title='In progress task', project=cls.project,
                                            assignee=cls.dev_a, created_by=cls.pm, status='IN_PROGRESS')

    def test_valid_transition_applied(self):
        self.client.force_login(self.dev_a)
        self.client.post(reverse('task_status', args=[self.task_todo.pk]), {'status': 'IN_PROGRESS'})
        self.task_todo.refresh_from_db()
        self.assertEqual(self.task_todo.status, 'IN_PROGRESS')

    def test_invalid_transition_rejected_with_message(self):
        self.client.force_login(self.dev_a)
        resp = self.client.post(reverse('task_status', args=[self.task_todo.pk]),
                                {'status': 'COMPLETED'}, follow=True)
        self.task_todo.refresh_from_db()
        self.assertEqual(self.task_todo.status, 'TODO')
        self.assertContains(resp, 'Invalid transition')

    def test_skipping_review_rejected(self):
        self.client.force_login(self.dev_a)
        resp = self.client.post(reverse('task_status', args=[self.task_prog.pk]),
                                {'status': 'COMPLETED'}, follow=True)
        self.task_prog.refresh_from_db()
        self.assertEqual(self.task_prog.status, 'IN_PROGRESS')
        self.assertContains(resp, 'Invalid transition')

    def test_non_assignee_cannot_change_status(self):
        self.client.force_login(self.dev_b)   # project member but NOT the assignee
        resp = self.client.post(reverse('task_status', args=[self.task_todo.pk]),
                                {'status': 'IN_PROGRESS'})
        self.assertEqual(resp.status_code, 404)
        self.task_todo.refresh_from_db()
        self.assertEqual(self.task_todo.status, 'TODO')


class TaskScopeTests(TestCase):
    """/my-tasks/ must return different data per role."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user('scadmin', 'scadmin@t.com', 'pw12345!', role='ADMIN')
        cls.pm = User.objects.create_user('scpm', 'scpm@t.com', 'pw12345!', role='PROJECT_MANAGER')
        cls.other_pm = User.objects.create_user('scpm2', 'scpm2@t.com', 'pw12345!', role='PROJECT_MANAGER')
        cls.dev = User.objects.create_user('scdev', 'scdev@t.com', 'pw12345!', role='DEVELOPER')

        cls.p1 = Project.objects.create(name='Scope One', manager=cls.pm,
                                        start_date='2026-10-01', deadline='2026-11-30')
        cls.p2 = Project.objects.create(name='Scope Two', manager=cls.other_pm,
                                        start_date='2026-10-01', deadline='2026-11-30')
        ProjectMember.objects.create(project=cls.p1, user=cls.dev)

        cls.t1 = Task.objects.create(title='Assigned to dev', project=cls.p1,
                                     assignee=cls.dev, created_by=cls.pm)
        cls.t2 = Task.objects.create(title='Unassigned in p1', project=cls.p1, created_by=cls.pm)
        cls.t3 = Task.objects.create(title='Other project task', project=cls.p2,
                                     created_by=cls.other_pm)

    def _task_ids(self, user):
        self.client.force_login(user)
        resp = self.client.get(reverse('my_tasks'))
        return {t.pk for t in resp.context['tasks']}

    def test_admin_sees_every_task(self):
        self.assertEqual(self._task_ids(self.admin), {self.t1.pk, self.t2.pk, self.t3.pk})

    def test_pm_sees_only_managed_projects(self):
        self.assertEqual(self._task_ids(self.pm), {self.t1.pk, self.t2.pk})

    def test_developer_sees_only_own_assignments(self):
        self.assertEqual(self._task_ids(self.dev), {self.t1.pk})


class TaskCreationGuardsTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.pm = User.objects.create_user('cgp', 'cgp@t.com', 'pw12345!', role='PROJECT_MANAGER')
        cls.dev = User.objects.create_user('cgd', 'cgd@t.com', 'pw12345!', role='DEVELOPER')
        cls.outsider = User.objects.create_user('cgo', 'cgo@t.com', 'pw12345!', role='DEVELOPER')
        cls.project = Project.objects.create(name='Guard Project', manager=cls.pm,
                                             start_date='2026-10-01', deadline='2026-11-30')
        ProjectMember.objects.create(project=cls.project, user=cls.dev)

    def test_developer_cannot_create_task(self):
        self.client.force_login(self.dev)
        resp = self.client.post(reverse('task_create', args=[self.project.pk]),
                                {'title': 'Sneaky task'})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Task.objects.filter(project=self.project).count(), 0)

    def test_non_member_assignee_rejected(self):
        self.client.force_login(self.pm)
        resp = self.client.post(reverse('task_create', args=[self.project.pk]),
                                {'title': 'Cross-team task', 'assignee': str(self.outsider.pk)})
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(Task.objects.filter(project=self.project).count(), 0)

    def test_manager_creates_task_successfully(self):
        self.client.force_login(self.pm)
        resp = self.client.post(reverse('task_create', args=[self.project.pk]),
                                {'title': 'Proper task', 'assignee': str(self.dev.pk),
                                 'priority': 'HIGH'})
        self.assertEqual(resp.status_code, 302)
        task = Task.objects.get(project=self.project, title='Proper task')
        self.assertEqual(task.assignee, self.dev)
        self.assertEqual(task.created_by, self.pm)