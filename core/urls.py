from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

app_name = "core"

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('healthz/', views.health_check, name='healthz'),
    path('robots.txt', views.robots_txt, name='robots_txt'),
    path('portal/', views.PortalLoginView.as_view(), name='portal'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('about/', views.AboutOverviewView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('privacy-policy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('ai-assistant/reply/', views.ai_assistant_reply, name='ai_assistant_reply'),
    path('logout/', LogoutView.as_view(next_page='core:home'), name='logout'),
]