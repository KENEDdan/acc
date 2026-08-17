from django.test import TestCase, Client
from django.contrib.auth import get_user_model

User = get_user_model()


class RedirectToDashboardTests(TestCase):
    def test_redirects_to_role_specific_dashboard(self):
        user = User.objects.create_user(username='churchfin', password='x', role='church_finance', two_factor_enabled=True)
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/redirect/')
        self.assertRedirects(response, '/church/dashboard/finance/')

    def test_member_redirected_to_member_dashboard(self):
        user = User.objects.create_user(username='plainmember', password='x', role='member')
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/redirect/')
        self.assertRedirects(response, '/dashboard/member/')

    def test_anonymous_user_redirected_to_login(self):
        c = Client()
        response = c.get('/dashboard/redirect/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/portal/', response.url)


class ManageAccountsPermissionTests(TestCase):
    def test_only_superadmin_can_list_accounts(self):
        c = Client()
        response = c.get('/dashboard/accounts/')
        self.assertEqual(response.status_code, 302)

        non_super = User.objects.create_user(username='notsuper', password='x', role='church_info')
        c.force_login(non_super)
        response = c.get('/dashboard/accounts/')
        self.assertEqual(response.status_code, 302)

        superadmin = User.objects.create_user(username='super1', password='x', role='superadmin', two_factor_enabled=True)
        c.force_login(superadmin)
        response = c.get('/dashboard/accounts/')
        self.assertEqual(response.status_code, 200)

    def test_member_accounts_excluded_from_admin_accounts_list(self):
        superadmin = User.objects.create_user(username='super2', password='x', role='superadmin', two_factor_enabled=True)
        User.objects.create_user(username='regularmember', password='x', role='member')
        c = Client()
        c.force_login(superadmin)
        response = c.get('/dashboard/accounts/')
        self.assertNotContains(response, 'regularmember')


class CreateAccountTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(username='super3', password='x', role='superadmin', two_factor_enabled=True)
        self.client = Client()
        self.client.force_login(self.superadmin)

    def test_creating_an_account_forces_password_change(self):
        response = self.client.post('/dashboard/accounts/create/', {
            'username': 'newadmin', 'first_name': 'New', 'last_name': 'Admin', 'email': '',
            'phone_number': '', 'role': 'church_info',
            'password1': 'Sup3rSecurePass!123', 'password2': 'Sup3rSecurePass!123',
        })
        self.assertRedirects(response, '/dashboard/accounts/')
        new_user = User.objects.get(username='newadmin')
        self.assertTrue(new_user.must_change_password)
        self.assertEqual(new_user.role, 'church_info')


class AccountDetailEditToggleTests(TestCase):
    def setUp(self):
        self.superadmin = User.objects.create_user(username='super4', password='x', role='superadmin', two_factor_enabled=True)
        self.target = User.objects.create_user(username='target_admin', password='x', role='church_finance')
        self.client = Client()
        self.client.force_login(self.superadmin)

    def test_account_detail_view(self):
        response = self.client.get(f'/dashboard/accounts/{self.target.pk}/')
        self.assertEqual(response.status_code, 200)

    def test_account_edit_updates_role_and_contact_info(self):
        response = self.client.post(f'/dashboard/accounts/{self.target.pk}/edit/', {
            'first_name': 'Updated', 'last_name': 'Name', 'email': 'updated@example.com',
            'phone_number': '0900000001', 'role': 'church_info', 'is_active': 'on',
        })
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, 'church_info')
        self.assertEqual(self.target.first_name, 'Updated')
        self.assertRedirects(response, f'/dashboard/accounts/{self.target.pk}/')

    def test_toggle_active_flips_status_each_call(self):
        self.assertTrue(self.target.is_active)
        self.client.post(f'/dashboard/accounts/{self.target.pk}/toggle-active/')
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)

        self.client.post(f'/dashboard/accounts/{self.target.pk}/toggle-active/')
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)

    def test_member_accounts_cannot_be_managed_through_this_view(self):
        member = User.objects.create_user(username='justamember', password='x', role='member')
        response = self.client.get(f'/dashboard/accounts/{member.pk}/')
        self.assertEqual(response.status_code, 404)


class MemberDashboardTests(TestCase):
    def test_non_member_role_is_redirected_away(self):
        user = User.objects.create_user(username='notamember', password='x', role='church_info')
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/member/')
        self.assertEqual(response.status_code, 302)

    def test_member_role_can_view_own_dashboard(self):
        user = User.objects.create_user(username='amember', password='x', role='member')
        c = Client()
        c.force_login(user)
        response = c.get('/dashboard/member/')
        self.assertEqual(response.status_code, 200)
