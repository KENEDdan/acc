from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/new/', views.budget_create, name='budget_create'),
    path('budgets/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('budgets/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('budgets/queue/finance/', views.budget_queue_finance, name='budget_queue_finance'),
    path('budgets/queue/superadmin/', views.budget_queue_superadmin, name='budget_queue_superadmin'),
]
