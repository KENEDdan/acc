from django.db import models
from django.conf import settings
from finance.choices import Currency


class School(models.Model):
    name = models.CharField(max_length=200)
    location = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    joined_date = models.DateField(blank=True, null=True)

    def __str__(self):
        return self.name


class SchoolMember(models.Model):
    class MemberRole(models.TextChoices):
        STUDENT = 'student', 'Student'
        TEACHER = 'teacher', 'Teacher'

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='members')
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=10, choices=MemberRole.choices)
    contact_phone = models.CharField(max_length=20, blank=True)
    class_grade = models.CharField(max_length=50, blank=True)
    joined_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} - {self.school.name}"


class SchoolVolunteer(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='volunteers')
    full_name = models.CharField(max_length=150)
    contact_phone = models.CharField(max_length=20, blank=True)
    role_description = models.CharField(max_length=200, blank=True)
    joined_date = models.DateField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.full_name} (Volunteer - {self.school.name})"


class SchoolDisciple(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='disciples')
    full_name = models.CharField(max_length=150)
    phase_number = models.PositiveIntegerField(default=1)
    start_date = models.DateField()
    status = models.CharField(max_length=20, default='ongoing')

    def __str__(self):
        return f"{self.full_name} - {self.school.name}"


class SchoolActivity(models.Model):
    class Category(models.TextChoices):
        CLUB = 'club', 'School Club Grams'
        INTERNSHIP_DISCIPLESHIP = 'internship_discipleship', 'Internship Discipleship'
        PURPOSE_CONFERENCE = 'purpose_conference', 'Purpose Driven Conferences'
        TEACHERS_CONFERENCE = 'teachers_conference', 'Teachers Conferences'
        TRAUMA_AWARENESS = 'trauma_awareness', 'Trauma Awareness & Counselling'
        COUNSELLING = 'counselling', 'Counselling'
        PRAYERS_FASTING = 'prayers_fasting', 'Prayers & Fasting'
        LEADERSHIP_TRAINING = 'leadership_training', 'Leadership Trainings'
        LEADERSHIP_MEETING = 'leadership_meeting', 'Leadership Meetings'
        FELLOWSHIP = 'fellowship', 'Monthly Fellowship'
        INCENTIVES = 'incentives', 'Incentives & Support'
        VOLUNTEER_REFRESHER = 'volunteer_refresher', 'Volunteer Refresher Training'
        OTHER = 'other', 'Other'

    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='activities')
    category = models.CharField(max_length=30, choices=Category.choices)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='gym/activities/', blank=True, null=True)
    date = models.DateField(blank=True, null=True)
    schedule_text = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"{self.title} - {self.school.name}"


class AboutUs(models.Model):
    content = models.TextField()
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='gym_aboutus_edits')

    class Meta:
        verbose_name_plural = "About Us (GYM)"

    def __str__(self):
        return "GYM About Us"


class FinanceRecord(models.Model):
    class Type(models.TextChoices):
        INCOME = 'income', 'Income'
        EXPENSE = 'expense', 'Expense'

    class IncomeCategory(models.TextChoices):
        DONATION = 'donation', 'Donation'
        CHURCH = 'church', 'Church (ACC)'
        FREE_WILL = 'free_will', 'Free Will'

    class ExpenseCategory(models.TextChoices):
        ACTIVITIES = 'activities', 'Activities'
        OFFICE_MAINTENANCE = 'office_maintenance', 'Office Maintenance'
        MEDIA = 'media', 'Media'
        TRANSPORT = 'transport', 'Transportation'
        STATIONERY = 'stationery', 'Stationery Items'
        CLEANING = 'cleaning', 'Cleaning & Sanitation'
        OTHER = 'other', 'Other (Specify)'

    type = models.CharField(max_length=10, choices=Type.choices)
    income_category = models.CharField(max_length=30, choices=IncomeCategory.choices, blank=True)
    expense_category = models.CharField(max_length=30, choices=ExpenseCategory.choices, blank=True)
    other_category_note = models.CharField(max_length=200, blank=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    date = models.DateField()
    description = models.TextField(blank=True)
    school = models.ForeignKey(School, on_delete=models.SET_NULL, null=True, blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='gym_finance_records')
    recorded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        cat = self.income_category or self.expense_category or 'Other'
        return f"{self.get_type_display()} - {cat} - {self.amount}"