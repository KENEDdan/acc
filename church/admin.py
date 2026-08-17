from django.contrib import admin
from django.contrib import admin
from .models import (
    Branch, Compus, Activity, Member, DiscipleshipEnrollment,
    LiveService, MediaItem, LibraryResource, AboutUs, FinanceRecord,
    PastorElder, PrayerRequest, AttendanceRecord, CounselingSession,
    GivingAccount, GivingRecord,
)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'leader_name', 'capacity', 'disciples_count', 'is_active')
    list_filter = ('is_active',)


@admin.register(PastorElder)
class PastorElderAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'role_title', 'branch', 'is_active', 'display_order')
    list_filter = ('role_title', 'branch', 'is_active')
    search_fields = ('full_name',)


@admin.register(Compus)
class CompusAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'leader_name', 'started_date')


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'schedule_text', 'led_by', 'is_active')
    list_filter = ('category', 'is_active')


@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('member_id', 'full_name', 'membership_type', 'branch', 'contact_phone', 'is_active', 'registered_at')
    list_filter = ('membership_type', 'branch', 'is_active', 'gender')
    search_fields = ('full_name', 'member_id', 'contact_phone')
    readonly_fields = ('member_id', 'registered_at')


@admin.register(DiscipleshipEnrollment)
class DiscipleshipEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phase_number', 'status', 'start_date', 'end_date', 'facilitator')
    list_filter = ('status', 'phase_number')
    search_fields = ('full_name',)


@admin.register(LiveService)
class LiveServiceAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'is_live', 'started_at', 'started_by')
    list_filter = ('platform', 'is_live')


@admin.register(MediaItem)
class MediaItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'media_type', 'speaker', 'published_at', 'is_active')
    list_filter = ('media_type', 'is_active')
    search_fields = ('title', 'speaker')


@admin.register(LibraryResource)
class LibraryResourceAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'uploaded_at', 'is_active')
    list_filter = ('category', 'is_active')


@admin.register(AboutUs)
class AboutUsAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'updated_by')


@admin.register(FinanceRecord)
class FinanceRecordAdmin(admin.ModelAdmin):
    list_display = ('type', 'income_category', 'expense_category', 'amount', 'currency', 'date', 'branch', 'recorded_by')
    list_filter = ('type', 'income_category', 'expense_category', 'date')
    date_hierarchy = 'date'


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    list_display = ('date', 'branch', 'count', 'recorded_by', 'recorded_at')
    list_filter = ('branch', 'date')
    date_hierarchy = 'date'


@admin.register(PrayerRequest)
class PrayerRequestAdmin(admin.ModelAdmin):
    list_display = ('reference_code', 'submitted_by_name', 'status', 'is_urgent', 'created_at')
    list_filter = ('status', 'is_urgent')
    search_fields = ('reference_code', 'submitted_by_name', 'contact_phone')
    readonly_fields = ('reference_code',)


@admin.register(CounselingSession)
class CounselingSessionAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'status', 'scheduled_slot', 'contact_phone')
    list_filter = ('status',)
    search_fields = ('full_name', 'contact_phone')


@admin.register(GivingAccount)
class GivingAccountAdmin(admin.ModelAdmin):
    list_display = ('label', 'account_type', 'currency', 'is_active', 'display_order', 'updated_at')
    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('label', 'bank_name', 'momo_provider', 'account_number', 'momo_number')


@admin.register(GivingRecord)
class GivingRecordAdmin(admin.ModelAdmin):
    list_display = ('giver_name', 'purpose', 'amount', 'currency', 'status', 'submitted_at')
    list_filter = ('status', 'purpose', 'currency')
    search_fields = ('giver_name', 'contact_phone', 'contact_email', 'transaction_reference')
    readonly_fields = ('finance_record', 'reviewed_by', 'reviewed_at')