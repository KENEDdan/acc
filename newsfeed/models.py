from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

from core.validators import validate_image_extension


class FeedItem(models.Model):
    class Scope(models.TextChoices):
        MAIN = 'main', 'Main (All Sites)'
        CHURCH = 'church', 'Church (ACC)'
        GYM = 'gym', 'Global Youth Ministry'
        AFF = 'aff', "Apostles' Feet Foundation"

    class ItemType(models.TextChoices):
        NEWS = 'news', 'News'
        EVENT = 'event', 'Upcoming Event'
        REMINDER = 'reminder', 'Reminder'
        ENCOURAGEMENT = 'encouragement', 'Daily Encouragement'
        RECENT = 'recent', 'Recently Done'
        LIVE = 'live', 'Live Now'

    scope = models.CharField(max_length=10, choices=Scope.choices)
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    summary = models.CharField(max_length=300, help_text="Short teaser shown on the feed card")
    body = models.TextField()
    image = models.ImageField(upload_to='newsfeed/', blank=True, null=True, validators=[validate_image_extension])
    event_date = models.DateTimeField(blank=True, null=True, help_text="For events/reminders")
    is_pinned = models.BooleanField(default=False, help_text="Live items are auto-pinned")
    is_featured = models.BooleanField(default=False, help_text="Keep this item visible indefinitely, ignoring its expiry date")
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(blank=True, null=True, help_text="Item is hidden automatically after this time. Leave blank if Featured.")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='feed_items')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-published_at']

    def __str__(self):
        return f"[{self.get_scope_display()}] {self.title}"

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.title)[:200] or 'item'
            slug = base_slug
            n = 1
            while FeedItem.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base_slug}-{n}"
            self.slug = slug
        if self.item_type == self.ItemType.LIVE:
            self.is_pinned = True
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('newsfeed:detail', kwargs={'slug': self.slug})

    @property
    def is_expired(self):
        if self.is_featured or not self.expires_at:
            return False
        return timezone.now() >= self.expires_at


class FeedItemManager:
    """Query helper used across every landing page."""

    @staticmethod
    def active(scope=None):
        now = timezone.now()
        qs = FeedItem.objects.filter(
            models.Q(is_featured=True) | models.Q(expires_at__gt=now),
            is_active=True,
            published_at__lte=now,
        )
        if scope:
            qs = qs.filter(scope=scope)
        return qs