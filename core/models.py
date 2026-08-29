from django.db import models
from django.conf import settings


class SiteContact(models.Model):
    """Site-wide contact details shown on the public Contact page. A singleton,
    edited by the superadmin from the dashboard — see dashboard:contact_edit."""

    phone_primary = models.CharField(max_length=20, blank=True)
    phone_secondary = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    whatsapp_url = models.URLField(blank=True)
    map_embed_url = models.URLField(blank=True, help_text="Optional Google Maps embed URL")

    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Site Contact Info"

    def __str__(self):
        return "Site Contact Info"
