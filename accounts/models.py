from django.contrib.auth.models import AbstractUser
from django.db import models

from core.validators import validate_image_extension
from .fields import EncryptedCharField


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = 'superadmin', 'Superadmin'
        CHURCH_INFO = 'church_info', 'Church - Information Admin'
        CHURCH_FINANCE = 'church_finance', 'Church - Finance Admin'
        CHURCH_MEMBERSHIP = 'church_membership', 'Church - Membership Admin'
        CHURCH_DISCIPLESHIP = 'church_discipleship', 'Church - Discipleship Admin'
        CHURCH_MEDIA = 'church_media', 'Church - Live/Media Admin'
        GYM_INFO = 'gym_info', 'GYM - Information Admin'
        GYM_FINANCE = 'gym_finance', 'GYM - Finance Admin'
        GYM_SCHOOLS = 'gym_schools', 'GYM - Schools Admin'
        GYM_MEDIA = 'gym_media', 'GYM - Media Admin'
        AFF_INFO = 'aff_info', 'AFF - Information Admin'
        AFF_FINANCE = 'aff_finance', 'AFF - Finance Admin'
        MEMBER = 'member', 'Church Member'

    role = models.CharField(max_length=30, choices=Role.choices, default=Role.MEMBER)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_photo = models.ImageField(upload_to='profile_photos/', blank=True, null=True, validators=[validate_image_extension])
    must_change_password = models.BooleanField(
        default=False,
        help_text="If true, the user is forced to set a new password before doing anything else."
    )
    totp_secret = EncryptedCharField(max_length=255, blank=True, help_text="Encrypted at rest — see accounts.fields.EncryptedCharField")
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_backup_codes = models.TextField(blank=True, help_text="JSON list of hashed one-time backup codes")

    DASHBOARD_MAP = {
        Role.SUPERADMIN: 'dashboard:superadmin',
        Role.CHURCH_INFO: 'church:info_dashboard',
        Role.CHURCH_FINANCE: 'church:finance_dashboard',
        Role.CHURCH_MEMBERSHIP: 'church:membership_dashboard',
        Role.CHURCH_DISCIPLESHIP: 'church:discipleship_dashboard',
        Role.CHURCH_MEDIA: 'church:media_dashboard',
        Role.GYM_INFO: 'gym:info_dashboard',
        Role.GYM_FINANCE: 'gym:finance_dashboard',
        Role.GYM_SCHOOLS: 'gym:schools_dashboard',
        Role.GYM_MEDIA: 'gym:media_dashboard',
        Role.AFF_INFO: 'aff:info_dashboard',
        Role.AFF_FINANCE: 'aff:finance_dashboard',
        Role.MEMBER: 'dashboard:member',
    }
    

    def is_superadmin(self):
        return self.role == self.Role.SUPERADMIN

    def dashboard_url_name(self):
        return self.DASHBOARD_MAP.get(self.role, 'core:home')

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"