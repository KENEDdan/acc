from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Member, FinanceRecord, DiscipleshipEnrollment
from notifications.services import notify_superadmins
from audit.services import log_action


@receiver(post_save, sender=Member)
def notify_new_member(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New church member registered: {instance.full_name} ({instance.member_id})",
            link="/church/dashboard/membership/",
        )
        log_action(instance.registered_by, 'church', 'Member', instance)


@receiver(post_save, sender=DiscipleshipEnrollment)
def notify_new_disciple(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New discipleship enrollment: {instance.full_name} (Phase {instance.phase_number})",
            link="/church/dashboard/discipleship/",
        )
        log_action(instance.registered_by, 'church', 'DiscipleshipEnrollment', instance)


@receiver(post_save, sender=FinanceRecord)
def notify_new_church_finance(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New church finance entry: {instance.get_type_display()} - {instance.amount} {instance.currency}",
            link="/church/dashboard/finance/",
        )
        log_action(instance.recorded_by, 'church', 'FinanceRecord', instance)