from django.db import models
from django.conf import settings


class AuditLog(models.Model):
    class Scope(models.TextChoices):
        CHURCH = 'church', 'Church (ACC)'
        GYM = 'gym', 'Global Youth Ministry'
        AFF = 'aff', "Apostles' Feet Foundation"
        SYSTEM = 'system', 'System'

    class Action(models.TextChoices):
        CREATE = 'create', 'Created'
        UPDATE = 'update', 'Updated'
        DELETE = 'delete', 'Deleted'
        STATUS_CHANGE = 'status_change', 'Status Changed'

    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_entries')
    scope = models.CharField(max_length=10, choices=Scope.choices)
    action = models.CharField(max_length=15, choices=Action.choices, default=Action.CREATE)
    model_name = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    details = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_action_display()} {self.model_name}: {self.object_repr}"