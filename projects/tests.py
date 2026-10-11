from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from projects.models import Project, ProjectMember
from tasks.models import Task, Comment


class AuthorizationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user(username='admin', email='admin@t.com', password='pw12345!', role='ADMIN')
        cls.pm_a = User.objects.create_user(username='pma', email='pma@t.com', password='pw12345!', role='PROJECT_MANAGER')
        cls.pm_b = User.objects.create_user(username='pmb', email='pmb@t.com', password='pw12345!', role='PROJECT_MANAGER')
        cls.dev_a = User.objects.create_user(username='deva', email='deva@t.com', password='pw12345!', role='DEVELOPER')
        cls.dev_b = User.objects.create_user(username='devb', email='devb@t.com', password='pw12345!', role='DEVELOPER')

        cls.project_a = Project.objects.create(name='Project A', manager=cls.pm_a, start_date='2026-10-01', deadline='2026-11-30')
        cls.project_b = Project.objects.create(name='Project B', manager=cls.pm_b, start_date='2026-10-01', deadline='2026-11-30')
        ProjectMember.objects.create(project=cls.project_a, user=cls.dev_a)
        ProjectMember.objects.create(project=cls.project_b, user=cls.dev_b)

        cls.task_a = Task.objects.create(title='Task A', project=cls.project_a, assignee=cls.dev_a, created_by=cls.pm_a)
        cls.task_b = Task.objects.create(title='Task B', project=cls.project_b, assignee=cls.dev_b, created_by=cls.pm_b)

    def login(self, user):
        self.client.force_login(user)

    # --- Project-level authorization (the core challenge) ---

    def test_dev_can_open_own_project(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('project_detail', args=[self.project_a.pk]))
        self.assertEqual(resp.status_code, 200)

    def test_dev_cannot_open_foreign_project_by_url(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('project_detail', args=[self.project_b.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_pm_cannot_open_foreign_project(self):
        self.login(self.pm_a)
        resp = self.client.get(reverse('project_detail', args=[self.project_b.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_admin_can_open_any_project(self):
        self.login(self.admin)
        for p in (self.project_a, self.project_b):
            resp = self.client.get(reverse('project_detail', args=[p.pk]))
            self.assertEqual(resp.status_code, 200)

    def test_project_list_is_scoped(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('project_list'))
        self.assertContains(resp, 'Project A')
        self.assertNotContains(resp, 'Project B')

    # --- Task-level authorization ---

    def test_dev_cannot_open_foreign_task(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('task_detail', args=[self.task_b.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_dev_cannot_change_foreign_task_status(self):
        self.login(self.dev_a)
        self.client.post(reverse('task_status', args=[self.task_b.pk]), {'status': 'IN_PROGRESS'})
        self.task_b.refresh_from_db()
        self.assertEqual(self.task_b.status, 'TODO')   # unchanged

    def test_comment_on_foreign_task_blocked(self):
        self.login(self.dev_a)
        before = Comment.objects.count()
        self.client.post(reverse('comment_add', args=[self.task_b.pk]), {'body': 'hack'})
        self.assertEqual(Comment.objects.count(), before)

    # --- Workflow validation ---

    def test_valid_transition_allowed(self):
        self.login(self.dev_a)
        self.client.post(reverse('task_status', args=[self.task_a.pk]), {'status': 'IN_PROGRESS'})
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.status, 'IN_PROGRESS')

    def test_invalid_transition_blocked(self):
        self.login(self.dev_a)
        self.client.post(reverse('task_status', args=[self.task_a.pk]), {'status': 'COMPLETED'})  # skips review
        self.task_a.refresh_from_db()
        self.assertEqual(self.task_a.status, 'TODO')   # unchanged

    # --- Role gates & account security ---

    def test_dev_blocked_from_user_create(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('user_create'))
        self.assertEqual(resp.status_code, 403)

    def test_dev_blocked_from_label_manage(self):
        self.login(self.dev_a)
        resp = self.client.get(reverse('label_list'))
        self.assertEqual(resp.status_code, 403)

    def test_inactive_user_cannot_login(self):
        self.dev_a.is_active = False
        self.dev_a.save()
        logged_in = self.client.login(email='deva@t.com', password='pw12345!')
        self.assertFalse(logged_in)