from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AssistanceRequest, FinanceRecord
from notifications.services import notify_superadmins
from audit.services import log_action


@receiver(post_save, sender=AssistanceRequest)
def notify_aff_request(sender, instance, created, **kwargs):
    if created:
        if instance.status == AssistanceRequest.Status.PENDING:
            notify_superadmins(
                f"New AFF assistance request from {instance.full_name} - awaiting your approval",
                link="/dashboard/superadmin/",
            )
        log_action(instance.filled_by, 'aff', 'AssistanceRequest', instance)
    elif instance.status in (AssistanceRequest.Status.APPROVED, AssistanceRequest.Status.DECLINED, AssistanceRequest.Status.INFO_NEEDED, AssistanceRequest.Status.DISBURSED):
        log_action(instance.reviewed_by, 'aff', 'AssistanceRequest', instance, action='status_change', details=instance.get_status_display())


@receiver(post_save, sender=FinanceRecord)
def notify_aff_finance(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New AFF finance entry: {instance.get_type_display()} - {instance.amount} {instance.currency}",
            link="/dashboard/superadmin/",
        )
        log_action(instance.recorded_by, 'aff', 'FinanceRecord', instance)