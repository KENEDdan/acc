from django.db.models import TextChoices


class Currency(TextChoices):
    SSP = 'SSP', 'South Sudanese Pound (SSP)'
    USD = 'USD', 'US Dollar (USD)'