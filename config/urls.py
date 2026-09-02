from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from core.sitemaps import StaticViewSitemap

urlpatterns = [
    path('admin/', admin.site.urls),
    path('sitemap.xml', sitemap, {'sitemaps': {'static': StaticViewSitemap}}, name='sitemap'),
    path('', include('core.urls')),
    path('feed/', include('newsfeed.urls')),
    path('church/', include('church.urls')),
    path('gym/', include('gym.urls')),
    path('aff/', include('aff.urls')),
    path('finance/', include('finance.urls')),
    path('notifications/', include('notifications.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('account/', include('accounts.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)