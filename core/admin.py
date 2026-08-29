from django.contrib import admin
from .models import SiteContact


@admin.register(SiteContact)
class SiteContactAdmin(admin.ModelAdmin):
    list_display = ('phone_primary', 'email', 'updated_by', 'updated_at')
