from django.core import mail
from django.test import TestCase, Client
from django.contrib.auth import get_user_model

from church.models import Member
from accounts.services import create_member_account, reset_member_password
from accounts.two_factor import (
    role_requires_2fa, generate_totp_secret, get_totp_uri, verify_totp_code,
    generate_backup_codes, hash_backup_codes, verify_and_consume_backup_code,
    send_email_otp, verify_email_otp,
)

User = get_user_model()


class TotpSecretEncryptionTests(TestCase):
    """The totp_secret field is encrypted at rest with accounts.fields.EncryptedCharField —
    a raw database dump alone shouldn't hand over the ability to generate someone's 2FA codes."""

    def test_round_trips_through_the_orm(self):
        secret = generate_totp_secret()
        user = User.objects.create_user(username='totptest', password='x', role='church_finance')
        user.totp_secret = secret
        user.save()

        fresh = User.objects.get(pk=user.pk)
        self.assertEqual(fresh.totp_secret, secret)

    def test_raw_database_value_is_not_the_plaintext_secret(self):
        from django.db import connection

        secret = generate_totp_secret()
        user = User.objects.create_user(username='totptest2', password='x', role='church_finance')
        user.totp_secret = secret
        user.save()

        with connection.cursor() as cursor:
            cursor.execute("SELECT totp_secret FROM accounts_user WHERE id = %s", [user.pk])
            raw_value = cursor.fetchone()[0]

        self.assertNotEqual(raw_value, secret)
        self.assertNotIn(secret, raw_value)

    def test_blank_secret_stays_blank(self):
        user = User.objects.create_user(username='totptest3', password='x', role='member')
        self.assertEqual(user.totp_secret, '')
        fresh = User.objects.get(pk=user.pk)
        self.assertEqual(fresh.totp_secret, '')


class UserModelTests(TestCase):
    def test_is_superadmin(self):
        su = User.objects.create_user(username='su', password='x', role=User.Role.SUPERADMIN)
        member = User.objects.create_user(username='mem', password='x', role=User.Role.MEMBER)
        self.assertTrue(su.is_superadmin())
        self.assertFalse(member.is_superadmin())

    def test_dashboard_url_name_known_role(self):
        u = User.objects.create_user(username='fin', password='x', role=User.Role.CHURCH_FINANCE)
        self.assertEqual(u.dashboard_url_name(), 'church:finance_dashboard')

    def test_dashboard_url_name_defaults_to_home_for_unmapped_role(self):
        u = User(username='x', role='not-a-real-role')
        self.assertEqual(u.dashboard_url_name(), 'core:home')

    def test_str_includes_role(self):
        u = User.objects.create_user(username='jdoe', password='x', role=User.Role.MEMBER, first_name='Jane')
        self.assertIn('Jane', str(u))
        self.assertIn('Church Member', str(u))


class MemberAccountServiceTests(TestCase):
    def _make_member(self, **overrides):
        defaults = dict(
            full_name='Test Member', address='Somewhere', contact_phone='0900000000',
            date_of_birth='1990-01-01', gender='male', marital_status='single',
        )
        defaults.update(overrides)
        return Member.objects.create(**defaults)

    def test_create_member_account_sets_username_to_member_id(self):
        member = self._make_member()
        temp_password = create_member_account(member)
        member.refresh_from_db()
        self.assertIsNotNone(temp_password)
        self.assertTrue(member.user_id)
        self.assertEqual(member.user.username, member.member_id)
        self.assertEqual(member.user.role, User.Role.MEMBER)
        self.assertTrue(member.user.must_change_password)
        self.assertTrue(member.user.check_password(temp_password))

    def test_create_member_account_is_noop_if_already_has_account(self):
        member = self._make_member()
        create_member_account(member)
        member.refresh_from_db()
        result = create_member_account(member)
        self.assertIsNone(result)

    def test_reset_member_password_issues_new_temp_password_and_forces_change(self):
        member = self._make_member()
        create_member_account(member)
        member.refresh_from_db()
        user = member.user
        user.must_change_password = False
        user.save()

        new_password = reset_member_password(member)
        user.refresh_from_db()
        self.assertTrue(user.check_password(new_password))
        self.assertTrue(user.must_change_password)
        self.assertTrue(user.is_active)

    def test_reset_member_password_creates_account_if_none_exists(self):
        member = self._make_member()
        password = reset_member_password(member)
        member.refresh_from_db()
        self.assertIsNotNone(password)
        self.assertTrue(member.user_id)


class TwoFactorTests(TestCase):
    def test_role_requires_2fa(self):
        self.assertTrue(role_requires_2fa(User(role='superadmin')))
        self.assertTrue(role_requires_2fa(User(role='church_finance')))
        self.assertFalse(role_requires_2fa(User(role='member')))
        self.assertFalse(role_requires_2fa(User(role='church_info')))

    def test_totp_round_trip(self):
        secret = generate_totp_secret()
        import pyotp
        code = pyotp.TOTP(secret).now()
        self.assertTrue(verify_totp_code(secret, code))
        self.assertFalse(verify_totp_code(secret, '000000'))

    def test_verify_totp_code_handles_missing_input(self):
        self.assertFalse(verify_totp_code('', '123456'))
        self.assertFalse(verify_totp_code('SOMESECRET', ''))

    def test_get_totp_uri_includes_username_and_issuer(self):
        u = User(username='pastor')
        uri = get_totp_uri(u, 'SOMESECRET234567')
        self.assertIn('pastor', uri)
        self.assertIn('Apostolic', uri)

    def test_backup_codes_hash_and_single_use(self):
        codes = generate_backup_codes(count=3)
        self.assertEqual(len(codes), 3)
        user = User.objects.create_user(username='backupuser', password='x')
        user.two_factor_backup_codes = hash_backup_codes(codes)
        user.save()

        first_code = codes[0]
        self.assertTrue(verify_and_consume_backup_code(user, first_code))
        user.refresh_from_db()
        # Reusing the same code should now fail — it was consumed.
        self.assertFalse(verify_and_consume_backup_code(user, first_code))
        # A different, still-unused code should still work.
        self.assertTrue(verify_and_consume_backup_code(user, codes[1]))

    def test_verify_and_consume_backup_code_with_no_codes_set(self):
        user = User.objects.create_user(username='nocode', password='x')
        self.assertFalse(verify_and_consume_backup_code(user, 'anything'))


class FakeRequest:
    """Minimal stand-in for send_email_otp/verify_email_otp, which only touch request.session."""
    def __init__(self):
        self.session = {}


class EmailOtpTests(TestCase):
    def test_send_email_otp_requires_email_on_file(self):
        user = User.objects.create_user(username='noemail', password='x', role='member')
        self.assertFalse(send_email_otp(user, FakeRequest()))
        self.assertEqual(len(mail.outbox), 0)

    def test_send_email_otp_sends_and_stores_code(self):
        user = User.objects.create_user(username='hasemail', password='x', role='member', email='a@example.com')
        req = FakeRequest()
        self.assertTrue(send_email_otp(user, req))
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('a@example.com', mail.outbox[0].to)
        self.assertIn('2fa_email_code', req.session)

    def test_verify_email_otp_correct_code(self):
        user = User.objects.create_user(username='verifyok', password='x', role='member', email='b@example.com')
        req = FakeRequest()
        send_email_otp(user, req)
        self.assertTrue(verify_email_otp(req, req.session['2fa_email_code']))

    def test_verify_email_otp_wrong_code(self):
        user = User.objects.create_user(username='verifybad', password='x', role='member', email='c@example.com')
        req = FakeRequest()
        send_email_otp(user, req)
        self.assertFalse(verify_email_otp(req, '000000'))

    def test_verify_email_otp_is_single_use(self):
        user = User.objects.create_user(username='verifyonce', password='x', role='member', email='d@example.com')
        req = FakeRequest()
        send_email_otp(user, req)
        code = req.session['2fa_email_code']
        self.assertTrue(verify_email_otp(req, code))
        self.assertFalse(verify_email_otp(req, code))

    def test_verify_email_otp_expired(self):
        import datetime
        from django.utils import timezone
        user = User.objects.create_user(username='verifyexpired', password='x', role='member', email='e@example.com')
        req = FakeRequest()
        send_email_otp(user, req)
        code = req.session['2fa_email_code']
        req.session['2fa_email_code_sent_at'] = (timezone.now() - datetime.timedelta(minutes=11)).isoformat()
        self.assertFalse(verify_email_otp(req, code))

    def test_verify_email_otp_with_no_pending_code(self):
        self.assertFalse(verify_email_otp(FakeRequest(), '123456'))


class TwoFactorEmailVerifyViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='viewtest2fa', password='Sup3rSecure!123', role='church_finance',
            two_factor_enabled=True, email='viewtest@example.com', totp_secret='JBSWY3DPEHPK3PXP',
        )

    def test_full_email_otp_login_flow(self):
        c = Client()
        r = c.post('/portal/', {'username': 'viewtest2fa', 'password': 'Sup3rSecure!123'})
        self.assertRedirects(r, '/account/2fa/verify/', fetch_redirect_response=False)

        r = c.post('/account/2fa/verify/', {'action': 'send_email_code'})
        self.assertEqual(r.status_code, 200)
        self.assertIn('2fa_email_code', c.session)

        code = c.session['2fa_email_code']
        r = c.post('/account/2fa/verify/', {'code': code, 'use_email': '1'})
        self.assertRedirects(r, '/dashboard/redirect/', fetch_redirect_response=False)

    def test_email_option_hidden_without_email_on_file(self):
        User.objects.create_user(
            username='noemail2fa', password='Sup3rSecure!123', role='church_finance',
            two_factor_enabled=True, totp_secret='JBSWY3DPEHPK3PXP',
        )
        c = Client()
        c.post('/portal/', {'username': 'noemail2fa', 'password': 'Sup3rSecure!123'})
        r = c.get('/account/2fa/verify/')
        self.assertNotContains(r, 'Email Me a Code')


class ForcePasswordChangeMiddlewareTests(TestCase):
    def test_must_change_password_redirects_away_from_other_pages(self):
        user = User.objects.create_user(username='mustchange', password='x', role=User.Role.MEMBER, must_change_password=True)
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/redirect/')
        self.assertRedirects(response, '/account/change-password/', fetch_redirect_response=False)

    def test_exempt_path_not_redirected(self):
        user = User.objects.create_user(username='mustchange2', password='x', role=User.Role.MEMBER, must_change_password=True)
        c = Client()
        c.force_login(user)
        response = c.get('/account/change-password/')
        self.assertNotEqual(response.status_code, 302)


class RequireTwoFactorMiddlewareTests(TestCase):
    def test_finance_role_without_2fa_redirected_to_setup(self):
        user = User.objects.create_user(username='needs2fa', password='x', role=User.Role.CHURCH_FINANCE)
        c = Client()
        c.force_login(user)
        response = c.get('/church/dashboard/finance/')
        self.assertRedirects(response, '/account/2fa/setup/', fetch_redirect_response=False)

    def test_member_role_never_forced_into_2fa(self):
        user = User.objects.create_user(username='plainmember', password='x', role=User.Role.MEMBER)
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/member/')
        self.assertEqual(response.status_code, 200)

    def test_finance_role_with_2fa_enabled_not_redirected(self):
        user = User.objects.create_user(
            username='has2fa', password='x', role=User.Role.CHURCH_FINANCE, two_factor_enabled=True,
        )
        c = Client()
        c.force_login(user)
        response = c.get('/church/dashboard/finance/')
        self.assertEqual(response.status_code, 200)
