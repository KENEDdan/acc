from django.urls import path
from .views import FeedItemDetailView

app_name = 'newsfeed'

urlpatterns = [
    path('item/<slug:slug>/', FeedItemDetailView.as_view(), name='detail'),
]