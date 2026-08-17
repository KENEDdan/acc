from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('change-password/', views.change_password, name='change_password'),

    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
        success_url='/account/password-reset/done/',
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/account/reset/done/',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),

    path('2fa/setup/', views.two_factor_setup, name='two_factor_setup'),
    path('2fa/backup-codes/', views.two_factor_backup_codes, name='two_factor_backup_codes'),
    path('2fa/manage/', views.two_factor_manage, name='two_factor_manage'),
    path('2fa/disable/', views.two_factor_disable, name='two_factor_disable'),
    path('2fa/regenerate-backup-codes/', views.two_factor_regenerate_backup_codes, name='two_factor_regenerate_backup_codes'),
    path('2fa/verify/', views.two_factor_verify, name='two_factor_verify'),
]