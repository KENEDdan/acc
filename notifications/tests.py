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
