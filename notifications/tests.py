from django.core import mail
from django.test import TestCase
from django.contrib.auth import get_user_model

from notifications.models import Notification
from notifications.services import notify_user, notify_role, notify_superadmins

User = get_user_model()


class NotificationServiceTests(TestCase):
    def test_notify_user_creates_single_notification(self):
        user = User.objects.create_user(username='alice', password='x', role=User.Role.MEMBER)
        notify_user(user, "Hello there", link="/somewhere/")
        note = Notification.objects.get(recipient=user)
        self.assertEqual(note.message, "Hello there")
        self.assertEqual(note.link, "/somewhere/")
        self.assertFalse(note.is_read)

    def test_notify_role_fans_out_to_active_users_of_that_role_only(self):
        User.objects.create_user(username='fin1', password='x', role=User.Role.CHURCH_FINANCE)
        User.objects.create_user(username='fin2', password='x', role=User.Role.CHURCH_FINANCE)
        User.objects.create_user(username='info1', password='x', role=User.Role.CHURCH_INFO)
        User.objects.create_user(username='fin_inactive', password='x', role=User.Role.CHURCH_FINANCE, is_active=False)

        notify_role('church_finance', "New entry needs review")

        recipients = set(Notification.objects.values_list('recipient__username', flat=True))
        self.assertEqual(recipients, {'fin1', 'fin2'})

    def test_notify_role_with_no_matching_users_creates_nothing(self):
        notify_role('gym_media', "Nobody home")
        self.assertEqual(Notification.objects.count(), 0)

    def test_notify_superadmins_fans_out_to_active_superadmins_only(self):
        User.objects.create_user(username='super1', password='x', role=User.Role.SUPERADMIN)
        User.objects.create_user(username='super2', password='x', role=User.Role.SUPERADMIN, is_active=False)
        User.objects.create_user(username='notsuper', password='x', role=User.Role.MEMBER)

        notify_superadmins("Please review")

        recipients = set(Notification.objects.values_list('recipient__username', flat=True))
        self.assertEqual(recipients, {'super1'})

    def test_notify_superadmins_emails_those_with_an_address_on_file(self):
        User.objects.create_user(username='super_with_email', password='x', role=User.Role.SUPERADMIN, email='a@example.com')
        User.objects.create_user(username='super_no_email', password='x', role=User.Role.SUPERADMIN)

        notify_superadmins("New AFF request needs review", link="/dashboard/superadmin/")

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['a@example.com'])
        self.assertIn("New AFF request needs review", mail.outbox[0].body)
        self.assertIn("/dashboard/superadmin/", mail.outbox[0].body)

    def test_notify_superadmins_with_no_email_sends_no_mail(self):
        User.objects.create_user(username='super_no_email2', password='x', role=User.Role.SUPERADMIN)
        notify_superadmins("Please review")
        self.assertEqual(len(mail.outbox), 0)

    def test_notify_user_and_notify_role_do_not_send_email(self):
        """Only notify_superadmins emails — notify_user/notify_role stay in-app only."""
        user = User.objects.create_user(username='plainuser', password='x', role=User.Role.CHURCH_FINANCE, email='b@example.com')
        notify_user(user, "Hello")
        notify_role('church_finance', "Something happened")
        self.assertEqual(len(mail.outbox), 0)
