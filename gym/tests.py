import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from gym.models import School, SchoolMember, FinanceRecord

User = get_user_model()


def make_school(**overrides):
    defaults = dict(name='Test School', location='Juba')
    defaults.update(overrides)
    return School.objects.create(**defaults)


class SchoolModelTests(TestCase):
    def test_school_str_is_name(self):
        school = make_school(name='Juba Model School')
        self.assertEqual(str(school), 'Juba Model School')

    def test_school_member_str_includes_school_name(self):
        school = make_school()
        member = SchoolMember.objects.create(school=school, full_name='Student One', role='student')
        self.assertIn('Test School', str(member))


class RolePermissionMixin:
    def login_as(self, role, **extra):
        extra.setdefault('two_factor_enabled', True)
        user = User.objects.create_user(username=f'user_{role}_{User.objects.count()}', password='x', role=role, **extra)
        c = Client()
        c.force_login(user)
        return c, user

    def assert_requires_role(self, url, wrong_role, method='get', data=None):
        anon = Client()
        response = getattr(anon, method)(url, data or {})
        self.assertEqual(response.status_code, 302)

        wrong_c, _ = self.login_as(wrong_role)
        response = getattr(wrong_c, method)(url, data or {})
        self.assertEqual(response.status_code, 302)

        super_c, _ = self.login_as('superadmin')
        response = getattr(super_c, method)(url, data or {})
        self.assertIn(response.status_code, (200, 302))


class GymViewPermissionTests(RolePermissionMixin, TestCase):
    def test_school_create_requires_schools_role(self):
        self.assert_requires_role('/gym/schools/new/', 'gym_finance')

    def test_finance_create_requires_finance_role(self):
        self.assert_requires_role('/gym/finance/new/', 'gym_schools')

    def test_finance_reports_requires_finance_role(self):
        self.assert_requires_role('/gym/finance/reports/', 'gym_schools')

    def test_feed_item_create_requires_info_role(self):
        self.assert_requires_role('/gym/feed/new/', 'gym_media')

    def test_school_activity_create_requires_media_role(self):
        self.assert_requires_role('/gym/activities/new/', 'gym_info')


class GymFinanceConfirmFlowTests(TestCase):
    def setUp(self):
        self.school = make_school()
        self.user = User.objects.create_user(username='gymfin', password='x', role='gym_finance', two_factor_enabled=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_submitting_without_confirm_shows_preview_and_does_not_save(self):
        response = self.client.post('/gym/finance/new/', {
            'type': 'income', 'income_category': 'donation', 'amount': '150', 'currency': 'SSP',
            'date': '2026-01-10', 'school': self.school.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'gym/finance_confirm.html')
        self.assertEqual(FinanceRecord.objects.count(), 0)

    def test_confirm_flag_saves_the_record(self):
        response = self.client.post('/gym/finance/new/', {
            'type': 'income', 'income_category': 'donation', 'amount': '150', 'currency': 'SSP',
            'date': '2026-01-10', 'school': self.school.pk, 'confirm': '1',
        })
        self.assertRedirects(response, '/gym/dashboard/finance/')
        self.assertEqual(FinanceRecord.objects.count(), 1)
        record = FinanceRecord.objects.get()
        self.assertEqual(record.recorded_by, self.user)

    def test_finance_report_export_returns_csv(self):
        FinanceRecord.objects.create(type='income', income_category='donation', amount=100, currency='SSP', date=datetime.date(2026, 1, 1))
        response = self.client.get('/gym/finance/reports/export/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/csv')
