from django.db import models
from django.conf import settings
from finance.choices import Currency
from core.validators import validate_image_extension


class Activity(models.Model):
    class Category(models.TextChoices):
        PROGRAM = 'program', 'Support Program'
        OUTREACH = 'outreach', 'Community Outreach'
        TRAINING = 'training', 'Training & Mentorship'
        COMMUNITY_EVENT = 'community_event', 'Community Event'
        ADMINISTRATIVE = 'administrative', 'Administrative'
        FUNDRAISING = 'fundraising', 'Fundraising'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField()
    image = models.ImageField(upload_to='aff/activities/', blank=True, null=True, validators=[validate_image_extension])
    schedule_text = models.CharField(max_length=200, blank=True, help_text="e.g. Every last Saturday of the month")
    led_by = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Activities"

    def __str__(self):
        return self.name


class AssistanceRequest(models.Model):
    class Sex(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class MaritalStatus(models.TextChoices):
        MARRIED = 'married', 'Married'
        SINGLE = 'single', 'Single'

    class MembershipType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full Time Member'
        ASSOCIATE = 'associate', 'Associate Member'
        ONLINE = 'online', 'Online Member'

    class HelpDirectedTo(models.TextChoices):
        ME = 'me', 'Me'
        SPOUSE = 'spouse', 'Spouse'
        PARENT = 'parent', 'Parent'
        CHILD = 'child', 'Child'
        OTHERS = 'others', 'Others'

    class NeedCategory(models.TextChoices):
        SCHOOL_FEES = 'school_fees', 'School Fees'
        TUITION = 'tuition', 'Tuition Fees'
        MEDICAL = 'medical', 'Medical Bills'
        TRANSPORT = 'transport', 'Transportation'
        RENT = 'rent', 'Rent'
        FEEDING = 'feeding', 'Feeding'
        OTHER = 'other', 'Other (Specify)'

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted — Awaiting AFF Review'
        PENDING = 'pending', 'Pending Approval'
        APPROVED = 'approved', 'Approved'
        DECLINED = 'declined', 'Declined'
        INFO_NEEDED = 'info_needed', 'More Information Needed'
        DISBURSED = 'disbursed', 'Disbursed'

    # (A) Personal information
    full_name = models.CharField(max_length=150)
    request_date = models.DateField()
    tel = models.CharField(max_length=20)
    sex = models.CharField(max_length=10, choices=Sex.choices)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices)
    residential_address = models.CharField(max_length=250)
    occupation = models.CharField(max_length=150, blank=True)
    family = models.CharField(max_length=250, blank=True)

    # (B) Membership information
    membership_type = models.CharField(max_length=15, choices=MembershipType.choices)
    membership_duration = models.CharField(max_length=100, blank=True)

    # (C) Spiritual information
    received_salvation = models.BooleanField(default=False)
    salvation_when_where = models.CharField(max_length=250, blank=True)
    salvation_experience = models.TextField(blank=True)
    gone_through_discipleship = models.BooleanField(default=False)
    department_serving = models.CharField(max_length=150, blank=True)

    # Need details
    how_church_can_help = models.TextField()
    need_category = models.CharField(max_length=20, choices=NeedCategory.choices)
    other_need_note = models.CharField(max_length=200, blank=True)
    amount_have = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_requested = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    help_directed_to = models.CharField(max_length=10, choices=HelpDirectedTo.choices)
    help_directed_other = models.CharField(max_length=150, blank=True)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING)
    filled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='aff_requests_filled')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='aff_requests_reviewed')
    reviewed_at = models.DateTimeField(blank=True, null=True)
    review_notes = models.TextField(blank=True)
    disbursed_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    disbursed_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"


class AboutUs(models.Model):
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='aff_aboutus_edits')

    class Meta:
        verbose_name_plural = "About Us (AFF)"

    def __str__(self):
        return "AFF About Us"


class FinanceRecord(models.Model):
    class Type(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense (Disbursement)'

    class IncomeCategory(models.TextChoices):
        CHURCH_DONOR = 'church_donor', 'Church ACC (Main Donor)'
        DONATIONS_GRANTS = 'donations_grants', 'Donations & Grants'
        FREE_WILL = 'free_will', 'Free Will'
        OTHER = 'other', 'Other (Specify)'

    type = models.CharField(max_length=10, choices=Type.choices)
    income_category = models.CharField(max_length=30, choices=IncomeCategory.choices, blank=True)
    other_category_note = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    date = models.DateField()
    description = models.TextField(blank=True)
    related_request = models.ForeignKey(AssistanceRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_entries')
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='aff_finance_records')
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.get_type_display()} - {self.amount}"


class CashReconciliation(models.Model):
    date = models.DateField()
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    cash_at_hand = models.DecimalField(max_digits=12, decimal_places=2)
    source = models.CharField(max_length=250, help_text="Where this cash came from")
    system_recorded_balance = models.DecimalField(max_digits=12, decimal_places=2, help_text="System total at time of check")
    discrepancy = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        self.discrepancy = self.cash_at_hand - self.system_recorded_balance
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Reconciliation {self.date} - Discrepancy: {self.discrepancy}"