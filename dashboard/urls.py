from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path('redirect/', views.redirect_to_dashboard, name='redirect'),
    path('superadmin/', views.superadmin_dashboard, name='superadmin'),
    path('accounts/', views.manage_accounts, name='accounts'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('member/', views.member_dashboard, name='member'),
]