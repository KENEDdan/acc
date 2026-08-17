from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .forms import AdminAccountCreateForm, AdminAccountEditForm
from audit.services import log_action
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.db.models import Sum
from django.utils import timezone
from django.contrib.auth import get_user_model

from church.models import Member, Branch, DiscipleshipEnrollment, PastorElder, PrayerRequest, AttendanceRecord, CounselingSession, GivingRecord
from church.models import FinanceRecord as ChurchFinanceRecord
from gym.models import School, SchoolMember, SchoolVolunteer, SchoolDisciple
from gym.models import FinanceRecord as GymFinanceRecord
from aff.models import AssistanceRequest
from aff.models import FinanceRecord as AffFinanceRecord
from finance.utils import currency_breakdown

User = get_user_model()


@login_required
def redirect_to_dashboard(request):
    user = request.user
    url_name = user.dashboard_url_name()
    try:
        return redirect(reverse(url_name))
    except NoReverseMatch:
        return render(request, "dashboard/coming_soon.html", {"role": user.get_role_display()})


@login_required
def superadmin_dashboard(request):
    if not request.user.is_superadmin():
        return redirect('dashboard:redirect')

    church_income_qs = ChurchFinanceRecord.objects.filter(type=ChurchFinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
    church_expense_qs = ChurchFinanceRecord.objects.filter(type=ChurchFinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))

    gym_income_qs = GymFinanceRecord.objects.filter(type=GymFinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
    gym_expense_qs = GymFinanceRecord.objects.filter(type=GymFinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))

    aff_income_qs = AffFinanceRecord.objects.filter(type=AffFinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
    aff_disbursed_qs = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.DISBURSED).values('currency').annotate(total=Sum('disbursed_amount'))

    context = {
        'member_count': Member.objects.filter(is_active=True).count(),
        'branch_count': Branch.objects.filter(is_active=True).count(),
        'pastor_elder_count': PastorElder.objects.filter(is_active=True).count(),
        'discipleship_count': DiscipleshipEnrollment.objects.filter(status='ongoing').count(),
        'church_breakdown': currency_breakdown(church_income_qs, church_expense_qs),

        'school_count': School.objects.filter(is_active=True).count(),
        'gym_member_count': SchoolMember.objects.filter(is_active=True).count(),
        'gym_volunteer_count': SchoolVolunteer.objects.filter(is_active=True).count(),
        'gym_disciple_count': SchoolDisciple.objects.count(),
        'gym_breakdown': currency_breakdown(gym_income_qs, gym_expense_qs),

        'aff_breakdown': currency_breakdown(aff_income_qs, aff_disbursed_qs),
        'aff_pending_requests': AssistanceRequest.objects.filter(status=AssistanceRequest.Status.PENDING),

        'forwarded_prayer_requests': PrayerRequest.objects.filter(status=PrayerRequest.Status.FORWARDED),
        'recent_attendance': AttendanceRecord.objects.all()[:5],
        'todays_counseling_current': CounselingSession.objects.filter(
            scheduled_slot__date=timezone.now().date(), status=CounselingSession.Status.CURRENT
        ).first(),
        'todays_counseling_waiting': CounselingSession.objects.filter(
            scheduled_slot__date=timezone.now().date(), status=CounselingSession.Status.SCHEDULED
        ).count(),

        'leaders': User.objects.filter(is_active=True).exclude(role=User.Role.MEMBER).order_by('role'),
        'notifications': request.user.notifications.all()[:20],
    }
    return render(request, "dashboard/superadmin_dashboard.html", context)


def _is_superadmin(user):
    return user.is_authenticated and user.is_superadmin()


@login_required
@user_passes_test(_is_superadmin, login_url='/dashboard/redirect/')
def manage_accounts(request):
    accounts = User.objects.exclude(role=User.Role.MEMBER).order_by('role', 'username')
    return render(request, 'dashboard/accounts_list.html', {'accounts': accounts})


@login_required
@user_passes_test(_is_superadmin, login_url='/dashboard/redirect/')
def create_account(request):
    if request.method == 'POST':
        form = AdminAccountCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.must_change_password = True
            user.save()
            log_action(request.user, 'system', 'User', user, details=f"Role: {user.get_role_display()}")
            messages.success(request, f"Account '{user.username}' created as {user.get_role_display()}.")
            return redirect('dashboard:accounts')
    else:
        form = AdminAccountCreateForm()
    return render(request, 'dashboard/account_create.html', {'form': form})


@login_required
@user_passes_test(_is_superadmin, login_url='/dashboard/redirect/')
def account_detail(request, pk):
    account = get_object_or_404(User.objects.exclude(role=User.Role.MEMBER), pk=pk)
    return render(request, 'dashboard/account_detail.html', {'account': account})


@login_required
@user_passes_test(_is_superadmin, login_url='/dashboard/redirect/')
def account_edit(request, pk):
    account = get_object_or_404(User.objects.exclude(role=User.Role.MEMBER), pk=pk)
    if request.method == 'POST':
        form = AdminAccountEditForm(request.POST, instance=account)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'system', 'User', obj, action='update', details=f"Role: {obj.get_role_display()}")
            messages.success(request, f"Account '{obj.username}' updated.")
            return redirect('dashboard:account_detail', pk=obj.pk)
    else:
        form = AdminAccountEditForm(instance=account)
    return render(request, 'dashboard/account_edit.html', {'form': form, 'account': account})


@login_required
@user_passes_test(_is_superadmin, login_url='/dashboard/redirect/')
def account_toggle_active(request, pk):
    account = get_object_or_404(User.objects.exclude(role=User.Role.MEMBER), pk=pk)
    if request.method == 'POST':
        account.is_active = not account.is_active
        account.save(update_fields=['is_active'])
        log_action(
            request.user, 'system', 'User', account,
            action='update', details=('Activated' if account.is_active else 'Deactivated'),
        )
        messages.success(request, f"Account '{account.username}' {'activated' if account.is_active else 'deactivated'}.")
    return redirect('dashboard:account_detail', pk=account.pk)


@login_required
def member_dashboard(request):
    if request.user.role != User.Role.MEMBER:
        return redirect('dashboard:redirect')
    member_profile = getattr(request.user, 'member_profile', None)
    my_requests = AssistanceRequest.objects.filter(filled_by=request.user).order_by('-created_at')
    my_prayer_requests = PrayerRequest.objects.filter(submitted_by_user=request.user).order_by('-created_at')
    my_counseling_sessions = CounselingSession.objects.filter(booked_by_user=request.user).exclude(
        status=CounselingSession.Status.COMPLETED
    ).order_by('-requested_at')
    my_giving_records = GivingRecord.objects.filter(given_by_user=request.user).order_by('-submitted_at')[:5]
    return render(request, 'dashboard/member_dashboard.html', {
        'member_profile': member_profile,
        'my_requests': my_requests,
        'my_prayer_requests': my_prayer_requests,
        'my_counseling_sessions': my_counseling_sessions,
        'my_giving_records': my_giving_records,
    })