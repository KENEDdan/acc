from django.views.generic import DetailView
from .models import FeedItem


class FeedItemDetailView(DetailView):
    model = FeedItem
    template_name = 'newsfeed/detail.html'
    context_object_name = 'item'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'