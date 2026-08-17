from django.urls import path
from . import views

app_name = 'aff'

urlpatterns = [
    path('', views.AffHomeView.as_view(), name='home'),
    path('console/', views.AffConsoleView.as_view(), name='console'),
    path('about/', views.AffAboutUsView.as_view(), name='about'),

    path('requests/new/', views.request_create, name='request_create'),
    path('requests/<int:pk>/', views.request_detail, name='request_detail'),
    path('requests/<int:pk>/forward/', views.request_forward, name='request_forward'),
    path('requests/<int:pk>/review/', views.request_review, name='request_review'),
    path('requests/<int:pk>/resubmit/', views.request_resubmit, name='request_resubmit'),
    path('requests/<int:pk>/disburse/', views.request_disburse, name='request_disburse'),
    path('finance/new/', views.finance_record_create, name='finance_create'),
    path('finance/reports/', views.finance_reports, name='finance_reports'),
    path('finance/reports/export/', views.finance_report_export, name='finance_report_export'),
    path('finance/<int:pk>/', views.finance_record_detail, name='finance_detail'),
    path('reconciliation/new/', views.reconciliation_create, name='reconciliation_create'),
    path('feed/new/', views.feed_item_create, name='feed_item_create'),

    path('dashboard/info/', views.InfoDashboardView.as_view(), name='info_dashboard'),
    path('dashboard/finance/', views.FinanceDashboardView.as_view(), name='finance_dashboard'),
]