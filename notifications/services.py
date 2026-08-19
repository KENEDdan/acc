from django.contrib.auth import get_user_model


def _email_users(users, subject, body):
    """Best-effort — a notification email failing to send shouldn't break whatever
    request triggered it, so failures are swallowed rather than raised."""
    from django.conf import settings
    from django.core.mail import send_mail

    for user in users:
        if not user.email:
            continue
        send_mail(
            subject=subject, message=body, from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email], fail_silently=True,
        )


def _absolute_link(link):
    from django.conf import settings
    if not link:
        return ''
    return link if link.startswith('http') else f"{settings.SITE_BASE_URL.rstrip('/')}{link}"


def notify_superadmins(message, link=""):
    """Fan out a notification to every active superadmin account — both in-app and by
    email, since a superadmin has full oversight and may not be watching the in-app
    bell icon for anything time-sensitive."""
    from .models import Notification
    User = get_user_model()
    superadmins = list(User.objects.filter(role=User.Role.SUPERADMIN, is_active=True))
    Notification.objects.bulk_create([
        Notification(recipient=u, message=message, link=link) for u in superadmins
    ])

    body = message
    absolute_link = _absolute_link(link)
    if absolute_link:
        body = f"{message}\n\nView it here: {absolute_link}"
    _email_users(superadmins, "Apostolic Campus Church — New Notification", body)


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
