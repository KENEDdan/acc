from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Sends a one-off test email using the currently configured EMAIL_* settings — "
        "run this after setting up real SMTP credentials in .env, before go-live, to "
        "confirm password-reset emails will actually be delivered."
    )

    def add_arguments(self, parser):
        parser.add_argument('to_address', help="Email address to send the test message to")

    def handle(self, *args, **options):
        to_address = options['to_address']

        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            self.stdout.write(self.style.WARNING(
                "EMAIL_BACKEND is still the console backend — this will print the "
                "message here instead of actually sending it. Set EMAIL_BACKEND, "
                "EMAIL_HOST, EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD in .env for a "
                "real delivery test."
            ))

        try:
            send_mail(
                subject="ACC Platform — test email",
                message=(
                    "This is a test email from the ACC platform to confirm outgoing "
                    "email is configured correctly. If you received this, password "
                    "reset emails will work too."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_address],
                fail_silently=False,
            )
        except Exception as exc:
            raise CommandError(f"Failed to send: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Sent to {to_address} via {settings.EMAIL_BACKEND}."))
