def notifications_context(request):
    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(is_read=False).count()
    else:
        unread_count = 0
    return {'unread_notifications_count': unread_count}


def site_contact_context(request):
    """Exposed globally (not just on the Contact page) so base.html can render
    address/phone into the Organization structured data on every page.
    social_links_json is pre-built here (json.dumps) rather than assembled by
    hand in the template — conditionally comma-joining an unknown subset of
    optional URLs in a template is exactly the kind of thing that produces
    invalid JSON (a trailing comma) depending on which fields are filled in."""
    import json
    from .models import SiteContact
    contact = SiteContact.objects.first()
    social_links = []
    if contact:
        social_links = [
            url for url in (contact.facebook_url, contact.instagram_url, contact.twitter_url) if url
        ]
    return {'site_contact': contact, 'social_links_json': json.dumps(social_links)}