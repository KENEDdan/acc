from django.contrib import admin
from .models import FeedItem


@admin.register(FeedItem)
class FeedItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'scope', 'item_type', 'is_active', 'is_pinned', 'published_at', 'expires_at')
    list_filter = ('scope', 'item_type', 'is_active')
    search_fields = ('title', 'summary', 'body')
    prepopulated_fields = {'slug': ('title',)}
    date_hierarchy = 'published_at'