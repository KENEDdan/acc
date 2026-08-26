from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from finance.choices import Currency
from core.validators import validate_image_extension


def validate_photo_size(file):
    """Keep uploaded photos to a sane size so a single upload can't fill up disk/DB storage."""
    max_size_mb = 5
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"Image file is too large. Maximum size is {max_size_mb}MB.")


validate_library_file_extension = FileExtensionValidator(
    allowed_extensions=['pdf', 'epub', 'doc', 'docx', 'ppt', 'pptx', 'txt'],
    message="Unsupported file type. Allowed: PDF, EPUB, DOC(X), PPT(X), TXT.",
)


def validate_library_file_size(file):
    """Books/documents can be bigger than a photo, but still bounded — an unrestricted
    FileField would otherwise let anyone with upload access fill the server's disk."""
    max_size_mb = 25
    if file.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File is too large. Maximum size is {max_size_mb}MB.")


class Branch(models.Model):
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200)
    leader_name = models.CharField(max_length=150, blank=True, help_text="Pastor in Charge or Elder")
    capacity = models.PositiveIntegerField(blank=True, null=True, help_text="Approximate seating / congregation capacity")
    disciples_count = models.PositiveIntegerField(default=0, help_text="Number of disciples currently at this branch")
    history = models.TextField(blank=True, help_text="A brief history of how this branch was founded")
    established_date = models.DateField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Compus(models.Model):
    """Smaller fellowship groups not yet at branch level."""
    name = models.CharField(max_length=150)
    location = models.CharField(max_length=200)
    leader_name = models.CharField(max_length=150, blank=True)
    started_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Compuses"

    def __str__(self):
        return self.name


class Activity(models.Model):
    class Category(models.TextChoices):
        SUNDAY_SERVICE = 'sunday_service', 'Sunday Service'
        COUNSELLING = 'counselling', 'Counselling Sessions'
        BAPTISM = 'baptism', 'Baptism'
        CHILD_DEDICATION = 'child_dedication', 'Children Dedication'
        WEDDING = 'wedding', 'Weddings'
        MONTHLY_MEETING = 'monthly_meeting', 'Monthly General Meeting'
        MUSIC_LESSONS = 'music_lessons', 'Teaching & Learning Musical Instruments'
        HOLY_COMMUNION = 'holy_communion', 'Holy Communion'
        DISCIPLESHIP = 'discipleship', 'Discipleship'
        EVANGELISM = 'evangelism', 'Evangelism'
        CHOIR = 'choir', 'Choir Practice'
        CHILDREN = 'children', "Children's Sessions"
        TEENAGERS = 'teenagers', 'Teenagers Sessions'
        PRAYERS = 'prayers', 'Prayers & Intercessions'
        CLEANING = 'cleaning', 'Church Cleaning'
        VISITATION = 'visitation', 'Elders Visitation'
        OUTREACH = 'outreach', 'Street Children Outreach'
        OTHER = 'other', 'Other'

    name = models.CharField(max_length=150)
    category = models.CharField(max_length=30, choices=Category.choices)
    description = models.TextField()
    image = models.ImageField(upload_to='church/activities/', blank=True, null=True, validators=[validate_image_extension])
    schedule_text = models.CharField(max_length=200, help_text="e.g. Every Sunday 9:00 AM - 10:00 PM")
    led_by = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Member(models.Model):
    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class MaritalStatus(models.TextChoices):
        SINGLE = 'single', 'Single'
        MARRIED = 'married', 'Married'
        WIDOWED = 'widowed', 'Widowed'
        DIVORCED = 'divorced', 'Divorced'

    class MembershipType(models.TextChoices):
        FULL = 'full', 'Full Member'
        ASSOCIATE = 'associate', 'Associate Member'
        ONLINE = 'online', 'Online Member'

    member_id = models.CharField(max_length=30, unique=True, blank=True)
    full_name = models.CharField(max_length=150)
    address = models.CharField(max_length=250)
    contact_phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True, help_text="Needed for the member to reset their own password by email")
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=Gender.choices)
    occupation = models.CharField(max_length=150, blank=True)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices)

    received_salvation = models.BooleanField(default=False)
    salvation_when = models.CharField(max_length=100, blank=True)
    salvation_where = models.CharField(max_length=150, blank=True)
    salvation_meaning = models.TextField(blank=True, help_text="What does salvation mean to them")
    salvation_story = models.TextField(blank=True, help_text="Who was there / what happened / brief story")

    health_status = models.TextField(blank=True)
    how_heard_about_church = models.CharField(max_length=250, blank=True)
    reason_to_join = models.TextField(blank=True)
    talents_gifts = models.TextField(blank=True)

    membership_type = models.CharField(max_length=15, choices=MembershipType.choices, default=MembershipType.FULL)
    is_old_member = models.BooleanField(default=False)
    prior_duration = models.CharField(max_length=100, blank=True, help_text="If old member, how long at the church")

    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='members')
    photo = models.ImageField(upload_to='church/members/', blank=True, null=True, validators=[validate_image_extension])

    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='members_registered')
    registered_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='member_profile', help_text="This member's own login account, created at registration"
    )

    def save(self, *args, **kwargs):
        if not self.member_id:
            year = timezone.now().year
            last = Member.objects.filter(member_id__startswith=f"ACC-{year}-").order_by('-id').first()
            next_num = 1
            if last and last.member_id:
                try:
                    next_num = int(last.member_id.split('-')[-1]) + 1
                except ValueError:
                    pass
            self.member_id = f"ACC-{year}-{next_num:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} ({self.member_id})"


class DiscipleshipEnrollment(models.Model):
    class Status(models.TextChoices):
        ONGOING = 'ongoing', 'Ongoing'
        COMPLETED = 'completed', 'Completed'
        DROPPED = 'dropped', 'Dropped'

    class Gender(models.TextChoices):
        MALE = 'male', 'Male'
        FEMALE = 'female', 'Female'

    class MaritalStatus(models.TextChoices):
        SINGLE = 'single', 'Single'
        MARRIED = 'married', 'Married'
        WIDOWED = 'widowed', 'Widowed'
        DIVORCED = 'divorced', 'Divorced'

    full_name = models.CharField(max_length=150)
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='discipleship_records')
    contact_phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=250, blank=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True)
    occupation = models.CharField(max_length=150, blank=True)
    marital_status = models.CharField(max_length=10, choices=MaritalStatus.choices, blank=True)

    received_salvation = models.BooleanField(default=False)
    salvation_when = models.CharField(max_length=100, blank=True)
    salvation_where = models.CharField(max_length=150, blank=True)
    salvation_meaning = models.TextField(blank=True)
    salvation_story = models.TextField(blank=True)

    health_status = models.TextField(blank=True)
    how_heard_about_church = models.CharField(max_length=250, blank=True)
    reason_to_join = models.TextField(blank=True, help_text="Why do they want to go through discipleship?")
    talents_gifts = models.TextField(blank=True)

    phase_number = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True, help_text="Auto-set ~3 months after start")
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.ONGOING)
    facilitator = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)

    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='discipleship_registered')
    registered_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.end_date and self.start_date:
            from dateutil.relativedelta import relativedelta
            self.end_date = self.start_date + relativedelta(months=3)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.full_name} - Phase {self.phase_number}"

class LiveService(models.Model):
    class Platform(models.TextChoices):
        YOUTUBE = 'youtube', 'YouTube'
        FACEBOOK = 'facebook', 'Facebook'
        ZOOM = 'zoom', 'Zoom'
        OTHER = 'other', 'Other'

    platform = models.CharField(max_length=15, choices=Platform.choices)
    stream_url = models.URLField()
    title = models.CharField(max_length=200, default="Live Service")
    is_live = models.BooleanField(default=False)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    started_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.title} ({'LIVE' if self.is_live else 'offline'})"


class MediaItem(models.Model):
    class MediaType(models.TextChoices):
        SERMON = 'sermon', 'Sermon'
        TEACHING = 'teaching', 'Teaching'

    media_type = models.CharField(max_length=10, choices=MediaType.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    youtube_url = models.URLField()
    speaker = models.CharField(max_length=150, blank=True)
    published_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='media_items')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-published_at']

    def __str__(self):
        return f"[{self.get_media_type_display()}] {self.title}"


class LibraryResource(models.Model):
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=150, blank=True)
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='church/library/covers/', blank=True, null=True, validators=[validate_image_extension])
    file = models.FileField(
        upload_to='church/library/', blank=True, null=True,
        validators=[validate_library_file_extension, validate_library_file_size],
    )
    external_url = models.URLField(blank=True)
    category = models.CharField(max_length=100, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='library_resources')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.title


class AboutUs(models.Model):
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='church_aboutus_edits')

    class Meta:
        verbose_name_plural = "About Us (Church)"

    def __str__(self):
        return "Church About Us"


class FinanceRecord(models.Model):
    class Type(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    class IncomeCategory(models.TextChoices):
        OFFERTORY = 'offertory', 'Offertory'
        TITHES = 'tithes', 'Tithes'
        PERSONAL_CONTRIBUTION = 'personal_contribution', 'Personal Contributions'
        DONATION = 'donation', 'Donations'
        FREE_WILL = 'free_will', 'Free Wills'

    class ExpenseCategory(models.TextChoices):
        EVANGELISM = 'evangelism', 'Evangelism'
        COMPUSES = 'compuses', 'Compuses'
        BRANCHES = 'branches', 'Branches'
        DISCIPLESHIP = 'discipleship', 'Discipleship Program'
        AFF = 'aff', 'AFF (Main Sponsor)'
        VISITATIONS = 'visitations', 'Visitations'
        QUARTERLY_PRAYER_FASTING = 'quarterly_prayer_fasting', 'Quarterly Prayer & Fasting (Refreshments)'
        TRANSPORT = 'transport', 'Transportation & Logistics'
        WATER = 'water', 'Water'
        CLEANING = 'cleaning', 'Cleaning & Sanitation'
        MONTHLY_PRAYER_FASTING = 'monthly_prayer_fasting', 'Monthly Prayers & Fasting'
        RETREATS = 'retreats', 'Special Retreats'
        WORKSHOPS = 'workshops', 'Spiritual Workshops'
        LEADERSHIP_TRAINING = 'leadership_training', 'Leadership Trainings'
        SEMINARS = 'seminars', 'Seminars'
        CRUSADES = 'crusades', 'Crusades'
        WAGES = 'wages', 'Wages & Salary'
        CHILDREN = 'children', 'Children Activities'
        GYM_SPONSOR = 'gym_sponsor', 'GYM (Sponsorship)'
        MEDIA = 'media', 'Media'
        OUTREACH = 'outreach', 'Street Children Outreach Programs'
        OTHER = 'other', 'Other (Specify)'

    type = models.CharField(max_length=10, choices=Type.choices)
    income_category = models.CharField(max_length=30, choices=IncomeCategory.choices, blank=True)
    expense_category = models.CharField(max_length=30, choices=ExpenseCategory.choices, blank=True)
    other_category_note = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    date = models.DateField()
    description = models.TextField(blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='church_finance_records')
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        cat = self.income_category or self.expense_category or 'Other'
        return f"{self.get_type_display()} - {cat} - {self.amount}"

class PastorElder(models.Model):
    """Public directory entry for a pastor or elder, added by the superadmin."""

    class RoleTitle(models.TextChoices):
        SENIOR_PASTOR = 'senior_pastor', 'Senior Pastor'
        PASTOR_IN_CHARGE = 'pastor_in_charge', 'Pastor in Charge'
        ASSOCIATE_PASTOR = 'associate_pastor', 'Associate Pastor'
        ASSISTANT_PASTOR = 'assistant_pastor', 'Assistant Pastor'
        ELDER = 'elder', 'Elder'
        DEACON = 'deacon', 'Deacon'
        OTHER = 'other', 'Other (Specify)'

    full_name = models.CharField(max_length=150)
    photo = models.ImageField(upload_to='church/leaders/', blank=True, null=True, validators=[validate_photo_size, validate_image_extension])
    role_title = models.CharField(max_length=30, choices=RoleTitle.choices)
    role_title_other = models.CharField(max_length=100, blank=True, help_text="Only used if 'Other' is selected above")
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='leaders', help_text="The branch this person serves or is serving in"
    )
    phone_number = models.CharField(max_length=20, blank=True, help_text="Optional — leave blank to keep this private")
    email = models.EmailField(blank=True, help_text="Optional — leave blank to keep this private")
    biography = models.TextField(help_text="A brief professional biography")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers are shown first on the public page")
    is_active = models.BooleanField(default=True)
    added_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pastors_elders_added'
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'full_name']
        verbose_name = "Pastor / Elder"
        verbose_name_plural = "Pastors & Elders"

    def display_role(self):
        if self.role_title == self.RoleTitle.OTHER and self.role_title_other:
            return self.role_title_other
        return self.get_role_title_display()

    def __str__(self):
        return f"{self.full_name} ({self.display_role()})"

class PrayerRequest(models.Model):
    """Submitted by members (from their dashboard) or anonymous visitors (from the public page).
    Goes to the Membership Admin first, who forwards it to the superadmin; any response
    flows back the same way it came up."""

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted — Awaiting Review'
        FORWARDED = 'forwarded', 'Forwarded to Superadmin'
        RESPONDED = 'responded', 'Responded'

    reference_code = models.CharField(max_length=20, unique=True, blank=True, help_text="Shown to anonymous submitters to check for a response later")
    submitted_by_name = models.CharField(max_length=150, blank=True, help_text="Optional — leave blank to stay anonymous")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Optional — only if you'd like someone to follow up with you")
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='prayer_requests')
    submitted_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='prayer_requests_submitted')

    request_text = models.TextField()
    is_urgent = models.BooleanField(default=False)

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SUBMITTED)
    response_text = models.TextField(blank=True)
    responded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='prayer_responses')
    responded_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.reference_code:
            import secrets
            self.reference_code = f"PR-{secrets.token_hex(4).upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.reference_code} - {self.submitted_by_name or 'Anonymous'}"


class AttendanceRecord(models.Model):
    """A simple headcount for a given service/date, optionally by branch.
    Recorded by the Membership Admin; feeds the weekly/monthly/annual reports."""

    date = models.DateField()
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='attendance_records')
    count = models.PositiveIntegerField(help_text="Total number who attended")
    notes = models.CharField(max_length=250, blank=True, help_text="e.g. 'Easter Sunday', 'combined service'")
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='attendance_recorded')
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-date']

    def __str__(self):
        return f"{self.date} - {self.branch or 'All Branches'} - {self.count}"

class GivingAccount(models.Model):
    """Bank or Mobile Money details shown on the public 'Give' page so people watching
    online can send in their tithes, offerings, or donations. Added/edited by the
    superadmin or the Finance Admin only."""

    class AccountType(models.TextChoices):
        BANK = 'bank', 'Bank Account'
        MOMO = 'momo', 'Mobile Money'

    account_type = models.CharField(max_length=10, choices=AccountType.choices)
    label = models.CharField(max_length=150, help_text="e.g. 'Main Offering Account' or 'MTN Mobile Money'")
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)

    # Bank fields
    bank_name = models.CharField(max_length=150, blank=True)
    account_name = models.CharField(max_length=150, blank=True, help_text="Name the account is registered under")
    account_number = models.CharField(max_length=50, blank=True)
    branch_name = models.CharField(max_length=150, blank=True, help_text="Bank branch, if applicable")
    swift_code = models.CharField(max_length=20, blank=True, help_text="For international transfers, if applicable")

    # Mobile Money fields
    momo_provider = models.CharField(max_length=100, blank=True, help_text="e.g. MTN Mobile Money, Digitel Money")
    momo_number = models.CharField(max_length=20, blank=True)
    momo_registered_name = models.CharField(max_length=150, blank=True, help_text="Name the mobile money line is registered under")

    instructions = models.TextField(blank=True, help_text="Optional note for givers, e.g. what reference to use")
    display_order = models.PositiveIntegerField(default=0, help_text="Lower numbers are shown first on the public Give page")
    is_active = models.BooleanField(default=True, help_text="Untick to hide from the public Give page without deleting it")

    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='giving_accounts_updated')
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['display_order', 'account_type', 'label']
        verbose_name = "Giving Account (Bank / MoMo)"
        verbose_name_plural = "Giving Accounts (Bank / MoMo)"

    def __str__(self):
        return f"{self.label} ({self.get_account_type_display()})"


class GivingRecord(models.Model):
    """A tithe/offering/donation submitted by a public visitor or a registered member,
    after they've sent money to one of the church's Giving Accounts (bank/MoMo) above.
    Reviewed by the Finance Admin (or superadmin), who confirms it — which posts a
    matching income entry to the Finance ledger — or rejects it with a note."""

    class Purpose(models.TextChoices):
        TITHE = 'tithe', 'Tithe'
        OFFERTORY = 'offertory', 'Offertory'
        DONATION = 'donation', 'Donation'
        FREE_WILL = 'free_will', 'Free Will Offering'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending Review'
        CONFIRMED = 'confirmed', 'Confirmed'
        REJECTED = 'rejected', 'Rejected'

    giver_name = models.CharField(max_length=150, blank=True, help_text="Optional — leave blank to give anonymously")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Optional — only if you'd like a receipt or follow-up")
    contact_email = models.EmailField(blank=True)
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='giving_records')
    given_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='giving_records')

    giving_account = models.ForeignKey(
        GivingAccount, on_delete=models.SET_NULL, null=True, blank=True, related_name='giving_records',
        help_text="Which bank / mobile money account the funds were sent to"
    )
    purpose = models.CharField(max_length=15, choices=Purpose.choices, default=Purpose.DONATION)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    transaction_reference = models.CharField(max_length=100, blank=True, help_text="Bank deposit slip / mobile money transaction ID, if you have one")
    proof_of_payment = models.ImageField(
        upload_to='church/giving/proofs/', blank=True, null=True, validators=[validate_photo_size, validate_image_extension],
        help_text="Optional — a screenshot or photo of the payment confirmation"
    )
    message = models.TextField(blank=True, help_text="Optional note to the church")

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    finance_record = models.OneToOneField(FinanceRecord, on_delete=models.SET_NULL, null=True, blank=True, related_name='giving_record')
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='giving_records_reviewed')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.CharField(max_length=250, blank=True, help_text="e.g. reason for rejecting")

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = "Giving / Donation Record"

    def __str__(self):
        return f"{self.giver_name or 'Anonymous'} - {self.amount} {self.currency} ({self.get_status_display()})"


class CounselingSession(models.Model):
    """Counseling booking for registered members or non-registered visitors alike.
    Sessions run Mondays and Wednesdays only, 8:00 AM-4:00 PM, one hour each.
    Requests go to the Membership Admin, who allocates a specific hour (the database
    enforces that no two people can ever be given the same slot). The pastor
    (superadmin) then works through that day's schedule via the 'Next' action."""

    class Status(models.TextChoices):
        REQUESTED = 'requested', 'Requested - Awaiting Scheduling'
        SCHEDULED = 'scheduled', 'Scheduled'
        CURRENT = 'current', 'Now Being Seen'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    VALID_WEEKDAYS = (0, 2)  # Monday, Wednesday (Python's date.weekday(): Monday=0)
    VALID_HOURS = range(8, 16)  # 8am through 3pm start times -> last slot ends 4pm

    full_name = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=20)
    member = models.ForeignKey(Member, on_delete=models.SET_NULL, null=True, blank=True, related_name='counseling_sessions')
    booked_by_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='counseling_sessions_booked')

    topic = models.CharField(max_length=200, blank=True, help_text="General topic only, optional - e.g. 'marriage', 'grief'. No need for details here.")
    preferred_date = models.DateField(help_text="Your preferred date - sessions run Mondays and Wednesdays, 8AM-4PM")

    scheduled_slot = models.DateTimeField(null=True, blank=True, help_text="The confirmed one-hour slot, Monday or Wednesday between 8AM and 4PM")

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.REQUESTED)

    requested_at = models.DateTimeField(auto_now_add=True)
    scheduled_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='counseling_sessions_scheduled')

    class Meta:
        ordering = ['scheduled_slot', '-requested_at']
        constraints = [
            models.UniqueConstraint(fields=['scheduled_slot'], name='unique_counseling_slot'),
        ]

    def __str__(self):
        return f"{self.full_name} - {self.get_status_display()}"