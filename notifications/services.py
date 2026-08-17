from django.contrib.auth import get_user_model


def notify_superadmins(message, link=""):
    """Fan out a notification to every active superadmin account."""
    from .models import Notification
    User = get_user_model()
    superadmins = User.objects.filter(role=User.Role.SUPERADMIN, is_active=True)
    Notification.objects.bulk_create([
        Notification(recipient=u, message=message, link=link) for u in superadmins
    ])


def notify_user(user, message, link=""):
    from .models import Notification
    Notification.objects.create(recipient=user, message=message, link=link)


def notify_role(role, message, link=""):
    """Fan out a notification to every active user with the given role."""
    from .models import Notification
    User = get_user_model()
    recipients = User.objects.filter(role=role, is_active=True)
    Notification.objects.bulk_create([
        Notification(recipient=u, message=message, link=link) for u in recipients
    ])