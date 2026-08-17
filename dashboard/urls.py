from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    path('redirect/', views.redirect_to_dashboard, name='redirect'),
    path('superadmin/', views.superadmin_dashboard, name='superadmin'),
    path('accounts/', views.manage_accounts, name='accounts'),
    path('accounts/create/', views.create_account, name='create_account'),
    path('accounts/<int:pk>/', views.account_detail, name='account_detail'),
    path('accounts/<int:pk>/edit/', views.account_edit, name='account_edit'),
    path('accounts/<int:pk>/toggle-active/', views.account_toggle_active, name='account_toggle_active'),
    path('member/', views.member_dashboard, name='member'),
]