from django.test import TestCase
from django.contrib.auth import get_user_model

from audit.models import AuditLog
from audit.services import log_action

User = get_user_model()


class LogActionTests(TestCase):
    def test_log_action_records_actor_scope_and_repr(self):
        actor = User.objects.create_user(username='admin1', password='x', role=User.Role.SUPERADMIN)
        log_action(actor, 'church', 'Member', 'Jane Doe (ACC-2026-0001)', action='update', details='Phone changed')

        entry = AuditLog.objects.get()
        self.assertEqual(entry.actor, actor)
        self.assertEqual(entry.scope, 'church')
        self.assertEqual(entry.action, 'update')
        self.assertEqual(entry.model_name, 'Member')
        self.assertEqual(entry.object_repr, 'Jane Doe (ACC-2026-0001)')
        self.assertEqual(entry.details, 'Phone changed')

    def test_log_action_defaults_to_create(self):
        log_action(None, 'system', 'User', 'someone')
        entry = AuditLog.objects.get()
        self.assertEqual(entry.action, 'create')

    def test_log_action_with_none_actor_does_not_crash(self):
        log_action(None, 'system', 'User', 'anonymous action')
        entry = AuditLog.objects.get()
        self.assertIsNone(entry.actor)

    def test_log_action_with_unsaved_actor_stores_none(self):
        unsaved_user = User(username='ghost')  # no pk yet
        log_action(unsaved_user, 'system', 'User', 'ghost action')
        entry = AuditLog.objects.get()
        self.assertIsNone(entry.actor)

    def test_object_repr_is_truncated_to_255_chars(self):
        long_repr = 'x' * 500
        log_action(None, 'system', 'User', long_repr)
        entry = AuditLog.objects.get()
        self.assertEqual(len(entry.object_repr), 255)
