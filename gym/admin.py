from django.contrib import admin
from .models import School, SchoolMember, SchoolVolunteer, SchoolDisciple, SchoolActivity, AboutUs, FinanceRecord


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'contact_person', 'is_active')
    list_filter = ('is_active',)


@admin.register(SchoolMember)
class SchoolMemberAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'school', 'role', 'class_grade', 'is_active')
    list_filter = ('school', 'role', 'is_active')
    search_fields = ('full_name',)


@admin.register(SchoolVolunteer)
class SchoolVolunteerAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'school', 'role_description', 'is_active')
    list_filter = ('school', 'is_active')


@admin.register(SchoolDisciple)
class SchoolDiscipleAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'school', 'phase_number', 'status', 'start_date')
    list_filter = ('school', 'status')


@admin.register(SchoolActivity)
class SchoolActivityAdmin(admin.ModelAdmin):
    list_display = ('title', 'school', 'category', 'date')
    list_filter = ('school', 'category')


@admin.register(AboutUs)
class GymAboutUsAdmin(admin.ModelAdmin):
    list_display = ('updated_at', 'updated_by')


@admin.register(FinanceRecord)
class GymFinanceRecordAdmin(admin.ModelAdmin):
    list_display = ('type', 'income_category', 'expense_category', 'amount', 'currency', 'date', 'school')
    list_filter = ('type', 'school', 'date')
    date_hierarchy = 'date'