from django.contrib import admin
from .models import Budget, BudgetComment


class BudgetCommentInline(admin.TabularInline):
    model = BudgetComment
    extra = 0
    readonly_fields = ('author', 'action', 'message', 'created_at')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('title', 'scope', 'category', 'amount', 'currency', 'status', 'submitted_by', 'updated_at')
    list_filter = ('scope', 'status', 'currency')
    search_fields = ('title', 'category')
    inlines = [BudgetCommentInline]
