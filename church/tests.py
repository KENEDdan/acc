import datetime

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.utils import IntegrityError
from django.utils import timezone

from church.models import (
    Member, DiscipleshipEnrollment, PrayerRequest, CounselingSession,
    GivingAccount, GivingRecord, FinanceRecord, AttendanceRecord, Branch,
    MediaItem, LibraryResource,
)
from newsfeed.models import FeedItem

User = get_user_model()


def make_member(**overrides):
    defaults = dict(
        full_name='Test Member', address='Somewhere', contact_phone='0900000000',
        date_of_birth=datetime.date(1990, 1, 1), gender='male', marital_status='single',
    )
    defaults.update(overrides)
    return Member.objects.create(**defaults)


class MemberModelTests(TestCase):
    def test_member_id_auto_generated_with_current_year_prefix(self):
        member = make_member()
        year = timezone.now().year
        self.assertTrue(member.member_id.startswith(f"ACC-{year}-"))

    def test_member_id_increments_sequentially(self):
        first = make_member(full_name='First')
        second = make_member(full_name='Second')
        first_num = int(first.member_id.split('-')[-1])
        second_num = int(second.member_id.split('-')[-1])
        self.assertEqual(second_num, first_num + 1)

    def test_member_id_not_overwritten_on_resave(self):
        member = make_member()
        original_id = member.member_id
        member.full_name = 'Renamed'
        member.save()
        self.assertEqual(member.member_id, original_id)


class DiscipleshipEnrollmentModelTests(TestCase):
    def test_end_date_auto_set_three_months_after_start(self):
        enrollment = DiscipleshipEnrollment.objects.create(
            full_name='Disciple One', start_date=datetime.date(2026, 1, 15),
        )
        self.assertEqual(enrollment.end_date, datetime.date(2026, 4, 15))

    def test_explicit_end_date_not_overridden(self):
        enrollment = DiscipleshipEnrollment.objects.create(
            full_name='Disciple Two', start_date=datetime.date(2026, 1, 1),
            end_date=datetime.date(2026, 12, 31),
        )
        self.assertEqual(enrollment.end_date, datetime.date(2026, 12, 31))


class PrayerRequestModelTests(TestCase):
    def test_reference_code_auto_generated(self):
        pr = PrayerRequest.objects.create(request_text='Please pray for my family')
        self.assertTrue(pr.reference_code.startswith('PR-'))

    def test_reference_codes_are_unique(self):
        first = PrayerRequest.objects.create(request_text='First request')
        second = PrayerRequest.objects.create(request_text='Second request')
        self.assertNotEqual(first.reference_code, second.reference_code)


class CounselingSessionModelTests(TestCase):
    def test_cannot_double_book_the_same_slot(self):
        slot = timezone.make_aware(datetime.datetime(2026, 3, 2, 9, 0))  # a Monday
        CounselingSession.objects.create(
            full_name='First Person', contact_phone='0911', preferred_date=slot.date(),
            scheduled_slot=slot, status=CounselingSession.Status.SCHEDULED,
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                CounselingSession.objects.create(
                    full_name='Second Person', contact_phone='0922', preferred_date=slot.date(),
                    scheduled_slot=slot, status=CounselingSession.Status.SCHEDULED,
                )


class LibraryResourceUploadValidationTests(TestCase):
    def test_disallowed_file_extension_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from church.forms import LibraryResourceForm

        bad_file = SimpleUploadedFile('malware.exe', b'fake exe content', content_type='application/octet-stream')
        form = LibraryResourceForm(data={'title': 'Test Book'}, files={'file': bad_file})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)

    def test_allowed_file_extension_accepted(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from church.forms import LibraryResourceForm

        good_file = SimpleUploadedFile('book.pdf', b'%PDF-1.4 fake pdf content', content_type='application/pdf')
        form = LibraryResourceForm(data={'title': 'Test Book'}, files={'file': good_file})
        self.assertTrue(form.is_valid())

    def test_oversized_file_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from church.forms import LibraryResourceForm

        big_file = SimpleUploadedFile('book.pdf', b'x' * (26 * 1024 * 1024), content_type='application/pdf')
        form = LibraryResourceForm(data={'title': 'Test Book'}, files={'file': big_file})
        self.assertFalse(form.is_valid())
        self.assertIn('file', form.errors)


class GivingRecordModelTests(TestCase):
    def test_defaults_to_pending_status(self):
        record = GivingRecord.objects.create(amount=100, currency='SSP')
        self.assertEqual(record.status, GivingRecord.Status.PENDING)

    def test_str_falls_back_to_anonymous(self):
        record = GivingRecord.objects.create(amount=50, currency='SSP')
        self.assertIn('Anonymous', str(record))


class RolePermissionMixin:
    """Shared helpers for hitting a URL as different roles."""

    def login_as(self, role, **extra):
        extra.setdefault('two_factor_enabled', True)  # roles like finance/superadmin would otherwise be bounced to 2FA setup
        user = User.objects.create_user(username=f'user_{role}_{User.objects.count()}', password='x', role=role, **extra)
        c = Client()
        c.force_login(user)
        return c, user

    def assert_requires_role(self, url, allowed_role, method='get', data=None):
        # Anonymous is redirected away.
        anon = Client()
        response = getattr(anon, method)(url, data or {})
        self.assertEqual(response.status_code, 302)

        # A wrong-role admin is redirected away too.
        wrong_c, _ = self.login_as('church_media' if allowed_role != 'church_media' else 'church_info')
        response = getattr(wrong_c, method)(url, data or {})
        self.assertEqual(response.status_code, 302)

        # Superadmin can always get in.
        super_c, _ = self.login_as('superadmin')
        response = getattr(super_c, method)(url, data or {})
        self.assertIn(response.status_code, (200, 302))
        return super_c


class MemberViewPermissionTests(RolePermissionMixin, TestCase):
    def test_member_create_requires_membership_role(self):
        self.assert_requires_role('/church/members/new/', 'church_membership')

    def test_member_list_requires_membership_role(self):
        self.assert_requires_role('/church/members/', 'church_membership')

    def test_membership_admin_can_edit_a_member(self):
        c, _ = self.login_as('church_membership')
        member = make_member()
        response = c.post(f'/church/members/{member.pk}/edit/', {
            'full_name': 'Updated Name', 'address': member.address, 'contact_phone': member.contact_phone,
            'date_of_birth': '1990-01-01', 'gender': 'male', 'marital_status': 'single',
            'membership_type': 'full',
        })
        member.refresh_from_db()
        self.assertEqual(member.full_name, 'Updated Name')
        self.assertRedirects(response, f'/church/members/{member.pk}/')


class DiscipleshipViewPermissionTests(RolePermissionMixin, TestCase):
    def test_discipleship_create_requires_discipleship_role(self):
        self.assert_requires_role('/church/discipleship/new/', 'church_discipleship')

    def test_discipleship_detail_and_edit_require_discipleship_role(self):
        enrollment = DiscipleshipEnrollment.objects.create(full_name='D1', start_date=datetime.date(2026, 1, 1))
        self.assert_requires_role(f'/church/discipleship/{enrollment.pk}/', 'church_discipleship')
        self.assert_requires_role(f'/church/discipleship/{enrollment.pk}/edit/', 'church_discipleship')

    def test_discipleship_admin_can_edit_enrollment(self):
        c, _ = self.login_as('church_discipleship')
        enrollment = DiscipleshipEnrollment.objects.create(full_name='D2', start_date=datetime.date(2026, 1, 1))
        response = c.post(f'/church/discipleship/{enrollment.pk}/edit/', {
            'full_name': 'D2 Renamed', 'phase_number': 2, 'start_date': '2026-01-01',
            'status': 'ongoing',
        })
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.full_name, 'D2 Renamed')
        self.assertRedirects(response, f'/church/discipleship/{enrollment.pk}/')


class FinanceViewPermissionTests(RolePermissionMixin, TestCase):
    def test_finance_create_requires_finance_role(self):
        self.assert_requires_role('/church/finance/new/', 'church_finance')

    def test_finance_reports_requires_finance_role(self):
        self.assert_requires_role('/church/finance/reports/', 'church_finance')


class FinanceConfirmFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='finadmin', password='x', role='church_finance', two_factor_enabled=True)
        self.client = Client()
        self.client.force_login(self.user)

    def test_submitting_without_confirm_shows_preview_and_does_not_save(self):
        response = self.client.post('/church/finance/new/', {
            'type': 'income', 'income_category': 'tithes', 'amount': '500', 'currency': 'SSP',
            'date': '2026-01-15', 'description': 'Sunday tithes',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'church/finance_confirm.html')
        self.assertEqual(FinanceRecord.objects.count(), 0)

    def test_confirm_flag_actually_saves_the_record(self):
        response = self.client.post('/church/finance/new/', {
            'type': 'income', 'income_category': 'tithes', 'amount': '500', 'currency': 'SSP',
            'date': '2026-01-15', 'description': 'Sunday tithes', 'confirm': '1',
        })
        self.assertRedirects(response, '/church/dashboard/finance/')
        self.assertEqual(FinanceRecord.objects.count(), 1)
        record = FinanceRecord.objects.get()
        self.assertEqual(record.recorded_by, self.user)
        self.assertEqual(record.amount, 500)

    def test_finance_detail_is_read_only_and_has_no_edit_action(self):
        record = FinanceRecord.objects.create(type='income', income_category='tithes', amount=10, currency='SSP', date=datetime.date(2026, 1, 1))
        response = self.client.get(f'/church/finance/{record.pk}/')
        self.assertEqual(response.status_code, 200)
        # There's deliberately no edit view for a confirmed finance entry — confirm the URL just doesn't exist.
        from django.urls import reverse, NoReverseMatch
        with self.assertRaises(NoReverseMatch):
            reverse('church:finance_edit', args=[record.pk])


class GivingFlowTests(TestCase):
    def setUp(self):
        self.account = GivingAccount.objects.create(
            account_type='bank', label='Main Account', bank_name='Test Bank',
            account_name='ACC', account_number='12345',
        )

    def test_anonymous_visitor_can_submit_a_giving_record(self):
        c = Client()
        response = c.post('/church/give/', {
            'giver_name': 'John Doe', 'giving_account': self.account.pk, 'purpose': 'tithe',
            'amount': '500', 'currency': 'SSP',
        })
        self.assertEqual(response.status_code, 200)
        record = GivingRecord.objects.get()
        self.assertEqual(record.giver_name, 'John Doe')
        self.assertIsNone(record.given_by_user)
        self.assertEqual(record.status, GivingRecord.Status.PENDING)

    def test_logged_in_member_submission_links_user_and_member_profile(self):
        member = make_member(full_name='Registered Giver')
        user = User.objects.create_user(username=member.member_id, password='x', role=User.Role.MEMBER)
        member.user = user
        member.save()
        c = Client()
        c.force_login(user)

        c.post('/church/give/', {
            'giving_account': self.account.pk, 'purpose': 'offertory', 'amount': '200', 'currency': 'SSP',
        })
        record = GivingRecord.objects.get()
        self.assertEqual(record.given_by_user, user)
        self.assertEqual(record.member, member)
        self.assertEqual(record.giver_name, 'Registered Giver')

    def test_confirming_a_giving_record_posts_a_finance_record_and_confirms_it(self):
        finance_admin = User.objects.create_user(username='finadmin2', password='x', role='church_finance', two_factor_enabled=True)
        record = GivingRecord.objects.create(amount=300, currency='SSP', purpose=GivingRecord.Purpose.TITHE)

        c = Client()
        c.force_login(finance_admin)
        response = c.post(f'/church/dashboard/finance/giving-records/{record.pk}/confirm/')

        record.refresh_from_db()
        self.assertRedirects(response, '/church/dashboard/finance/giving-records/')
        self.assertEqual(record.status, GivingRecord.Status.CONFIRMED)
        self.assertIsNotNone(record.finance_record)
        self.assertEqual(record.finance_record.income_category, FinanceRecord.IncomeCategory.TITHES)
        self.assertEqual(record.finance_record.amount, 300)

    def test_rejecting_a_giving_record_does_not_touch_finance_ledger(self):
        finance_admin = User.objects.create_user(username='finadmin3', password='x', role='church_finance', two_factor_enabled=True)
        record = GivingRecord.objects.create(amount=300, currency='SSP')

        c = Client()
        c.force_login(finance_admin)
        c.post(f'/church/dashboard/finance/giving-records/{record.pk}/reject/', {'review_note': 'No matching deposit found'})

        record.refresh_from_db()
        self.assertEqual(record.status, GivingRecord.Status.REJECTED)
        self.assertEqual(record.review_note, 'No matching deposit found')
        self.assertEqual(FinanceRecord.objects.count(), 0)

    def test_giving_accounts_management_requires_finance_role(self):
        anon = Client()
        response = anon.get('/church/dashboard/finance/giving-accounts/')
        self.assertEqual(response.status_code, 302)

        wrong_role = User.objects.create_user(username='wrongrole', password='x', role='church_media')
        c = Client()
        c.force_login(wrong_role)
        response = c.get('/church/dashboard/finance/giving-accounts/')
        self.assertEqual(response.status_code, 302)


class AttendanceTests(RolePermissionMixin, TestCase):
    def test_attendance_delete_requires_membership_role(self):
        record = AttendanceRecord.objects.create(date=datetime.date(2026, 1, 1), count=42)
        self.assert_requires_role(f'/church/attendance/{record.pk}/delete/', 'church_membership', method='post')

    def test_membership_admin_can_clear_a_record(self):
        c, _ = self.login_as('church_membership')
        record = AttendanceRecord.objects.create(date=datetime.date(2026, 1, 1), count=42)
        c.post(f'/church/attendance/{record.pk}/delete/')
        self.assertFalse(AttendanceRecord.objects.filter(pk=record.pk).exists())


class InfoAndMediaViewPermissionTests(RolePermissionMixin, TestCase):
    def test_feed_item_create_requires_info_role(self):
        self.assert_requires_role('/church/feed/new/', 'church_info')

    def test_media_item_create_requires_media_role(self):
        self.assert_requires_role('/church/media/new/', 'church_media')

    def test_library_item_create_requires_media_role(self):
        self.assert_requires_role('/church/library/new/', 'church_media')

    def test_media_admin_can_edit_a_sermon(self):
        c, _ = self.login_as('church_media')
        item = MediaItem.objects.create(media_type='sermon', title='Old Title', youtube_url='https://youtube.com/x')
        response = c.post(f'/church/media/{item.pk}/edit/', {
            'media_type': 'sermon', 'title': 'New Title', 'youtube_url': 'https://youtube.com/x',
        })
        item.refresh_from_db()
        self.assertEqual(item.title, 'New Title')
        self.assertRedirects(response, f'/church/media/{item.pk}/')

    def test_media_admin_can_edit_a_library_book(self):
        c, _ = self.login_as('church_media')
        book = LibraryResource.objects.create(title='Old Book Title')
        response = c.post(f'/church/library/{book.pk}/edit/', {'title': 'New Book Title'})
        book.refresh_from_db()
        self.assertEqual(book.title, 'New Book Title')
        self.assertRedirects(response, f'/church/library/{book.pk}/')

    def test_info_admin_can_edit_a_feed_item(self):
        c, _ = self.login_as('church_info')
        item = FeedItem.objects.create(
            scope=FeedItem.Scope.CHURCH, item_type=FeedItem.ItemType.NEWS, title='Old', summary='s', body='b',
            expires_at=timezone.now() + datetime.timedelta(days=1),
        )
        response = c.post(f'/church/feed/{item.pk}/edit/', {
            'item_type': 'news', 'title': 'New Title', 'summary': 'updated summary', 'body': 'updated body',
            'published_at': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'expires_at': (timezone.now() + datetime.timedelta(days=5)).strftime('%Y-%m-%dT%H:%M'),
        })
        item.refresh_from_db()
        self.assertEqual(item.title, 'New Title')
        self.assertRedirects(response, f'/church/feed/{item.pk}/')


class SuperadminOnlyViewTests(RolePermissionMixin, TestCase):
    def test_branch_create_requires_superadmin(self):
        anon = Client()
        response = anon.get('/church/branches/new/')
        self.assertEqual(response.status_code, 302)

        non_super_c, _ = self.login_as('church_membership')
        response = non_super_c.get('/church/branches/new/')
        self.assertEqual(response.status_code, 302)

        super_c, _ = self.login_as('superadmin')
        response = super_c.get('/church/branches/new/')
        self.assertEqual(response.status_code, 200)
