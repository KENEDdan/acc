from django.urls import path
from . import views

app_name = 'gym'

urlpatterns = [
    path('', views.GymHomeView.as_view(), name='home'),
    path('console/', views.GymConsoleView.as_view(), name='console'),
    path('about/', views.GymAboutUsView.as_view(), name='about'),
    path('schools/', views.SchoolListView.as_view(), name='schools'),
    path('schools/<int:pk>/', views.SchoolDetailView.as_view(), name='school_detail'),

    path('feed/new/', views.feed_item_create, name='feed_item_create'),
    path('schools/new/', views.school_create, name='school_create'),
    path('members/new/', views.school_member_create, name='school_member_create'),
    path('volunteers/new/', views.school_volunteer_create, name='school_volunteer_create'),
    path('disciples/new/', views.school_disciple_create, name='school_disciple_create'),
    path('activities/new/', views.school_activity_create, name='school_activity_create'),
    path('finance/new/', views.finance_create, name='finance_create'),

    path('dashboard/info/', views.InfoDashboardView.as_view(), name='info_dashboard'),
    path('dashboard/finance/', views.FinanceDashboardView.as_view(), name='finance_dashboard'),
    path('dashboard/schools/', views.SchoolsDashboardView.as_view(), name='schools_dashboard'),
    path('dashboard/media/', views.MediaDashboardView.as_view(), name='media_dashboard'),
]