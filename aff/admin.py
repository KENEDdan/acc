from django.contrib import admin
from .models import Activity, AssistanceRequest, AboutUs, FinanceRecord, CashReconciliation


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'schedule_text', 'led_by', 'is_active')
    list_filter = ('category', 'is_active')


@admin.register(AssistanceRequest)
class AssistanceRequestAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'need_category', 'amount_requested', 'status', 'request_date', 'filled_by', 'reviewed_by')
    list_filter = ('status', 'need_category', 'membership_type')
    search_fields = ('full_name', 'tel')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Personal Information', {'fields': ('full_name', 'request_date', 'tel', 'sex', 'marital_status', 'residential_address', 'occupation', 'family')}),
        ('Membership Information', {'fields': ('membership_type', 'membership_duration')}),
        ('Spiritual Information', {'fields': ('received_salvation', 'salvation_when_where', 'salvation_experience', 'gone_through_discipleship', 'department_serving')}),
        ('Need Details', {'fields': ('how_church_can_help', 'need_category', 'other_need_note', 'amount_have', 'amount_requested', 'currency', 'help_directed_to', 'help_directed_other')}),
        ('Approval Workflow', {'fields': ('status', 'filled_by', 'reviewed_by', 'reviewed_at', 'review_notes', 'disbursed_amount', 'disbursed_at')}),
    )


@admin.register(AboutUs)
class AffAboutUsAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'updated_by')


@admin.register(FinanceRecord)
class AffFinanceRecordAdmin(admin.ModelAdmin):
    list_display = ('type', 'income_category', 'amount', 'currency', 'date', 'related_request', 'recorded_by')
    list_filter = ('type', 'income_category', 'date')
    date_hierarchy = 'date'


@admin.register(CashReconciliation)
class CashReconciliationAdmin(admin.ModelAdmin):
    list_display = ('date', 'currency', 'cash_at_hand', 'system_recorded_balance', 'discrepancy', 'source', 'recorded_by')
    readonly_fields = ('discrepancy',)
    date_hierarchy = 'date'