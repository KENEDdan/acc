from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'scope', 'action', 'model_name', 'object_repr', 'actor')
    list_filter = ('scope', 'action')
    search_fields = ('object_repr', 'model_name')