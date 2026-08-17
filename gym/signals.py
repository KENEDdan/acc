from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import SchoolMember, FinanceRecord
from notifications.services import notify_superadmins
from audit.services import log_action


@receiver(post_save, sender=SchoolMember)
def notify_new_gym_member(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New GYM member at {instance.school.name}: {instance.full_name}",
            link="/gym/dashboard/schools/",
        )
        log_action(None, 'gym', 'SchoolMember', instance)


@receiver(post_save, sender=FinanceRecord)
def notify_new_gym_finance(sender, instance, created, **kwargs):
    if created:
        notify_superadmins(
            f"New GYM finance entry: {instance.get_type_display()} - {instance.amount} {instance.currency}",
            link="/gym/dashboard/finance/",
        )
        log_action(instance.recorded_by, 'gym', 'FinanceRecord', instance)