from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class StaticViewSitemap(Sitemap):
    """Public, unauthenticated pages worth indexing. Dashboards, portal login,
    and anything behind LoginRequiredMixin are deliberately excluded."""

    protocol = 'https'

    changefreq_map = {
        'core:home': 'daily',
        'church:home': 'daily',
        'gym:home': 'daily',
        'aff:home': 'daily',
        'church:live': 'hourly',
    }

    def items(self):
        return [
            'core:home', 'core:about', 'core:contact', 'core:privacy_policy',
            'church:home', 'church:about', 'church:activities', 'church:branches',
            'church:pastors_elders', 'church:live', 'church:sermons', 'church:teachings',
            'church:library', 'church:giving_create',
            'gym:home', 'gym:about', 'gym:schools',
            'aff:home', 'aff:about',
        ]

    def location(self, item):
        return reverse(item)

    def changefreq(self, item):
        return self.changefreq_map.get(item, 'weekly')

    def priority(self, item):
        return 1.0 if item in ('core:home', 'church:home') else 0.5
