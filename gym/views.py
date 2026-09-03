from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
import csv

from newsfeed.models import FeedItem, FeedItemManager
from finance.utils import currency_breakdown, period_breakdown, sanitize_csv_row
from finance.models import Budget
from audit.models import AuditLog
from audit.services import log_action
from core.utils import parse_about_content
from .models import School, SchoolMember, SchoolVolunteer, SchoolDisciple, SchoolActivity, AboutUs, FinanceRecord
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.utils import timezone as tz
from newsfeed.forms import FeedItemForm
from .forms import SchoolForm, SchoolMemberForm, SchoolVolunteerForm, SchoolDiscipleForm, SchoolActivityForm, GymFinanceForm


class GymHomeView(TemplateView):
    template_name = "gym/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['feed_items'] = FeedItemManager.active(scope=FeedItem.Scope.GYM)[:30]
        ctx['school_count'] = School.objects.filter(is_active=True).count()
        return ctx


class GymAboutUsView(TemplateView):
    template_name = "gym/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        about = AboutUs.objects.first()
        ctx['about'] = about
        ctx['about_blocks'] = parse_about_content(about.content) if about else []
        return ctx


class SchoolListView(ListView):
    model = School
    template_name = "gym/schools.html"
    context_object_name = "schools"
    queryset = School.objects.filter(is_active=True)


class SchoolDetailView(DetailView):
    model = School
    template_name = "gym/school_detail.html"
    context_object_name = "school"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        school = self.object
        ctx['members'] = school.members.filter(is_active=True)
        ctx['volunteers'] = school.volunteers.filter(is_active=True)
        ctx['disciples'] = school.disciples.all()
        ctx['activities'] = school.activities.all()
        return ctx


class RoleDashboardMixin(LoginRequiredMixin, UserPassesTestMixin):
    allowed_roles = ()

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superadmin() or u.role in self.allowed_roles)

    def handle_no_permission(self):
        from django.shortcuts import redirect
        return redirect('dashboard:redirect')


class InfoDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "gym/dashboards/info_dashboard.html"
    allowed_roles = ('gym_info',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_items'] = FeedItem.objects.filter(scope=FeedItem.Scope.GYM).order_by('-created_at')[:20]
        return ctx


class FinanceDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "gym/dashboards/finance_dashboard.html"
    allowed_roles = ('gym_finance',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        qs = FinanceRecord.objects.filter(date__gte=month_start)
        income_qs = qs.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        expense_qs = qs.filter(type=FinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, expense_qs)
        ctx['recent_records'] = FinanceRecord.objects.all()[:20]
        ctx['pending_budget_count'] = Budget.objects.filter(scope='gym').exclude(status=Budget.Status.APPROVED).count()
        return ctx


class SchoolsDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "gym/dashboards/schools_dashboard.html"
    allowed_roles = ('gym_schools',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['schools'] = School.objects.filter(is_active=True)
        ctx['total_members'] = SchoolMember.objects.filter(is_active=True).count()
        ctx['total_volunteers'] = SchoolVolunteer.objects.filter(is_active=True).count()
        ctx['total_disciples'] = SchoolDisciple.objects.count()
        return ctx


class MediaDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "gym/dashboards/media_dashboard.html"
    allowed_roles = ('gym_media',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_activities'] = SchoolActivity.objects.all()[:20]
        return ctx


class ConsoleAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    ministry_roles = ('gym_info', 'gym_finance', 'gym_schools', 'gym_media')

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superadmin() or u.role in self.ministry_roles)

    def handle_no_permission(self):
        from django.shortcuts import redirect
        return redirect('dashboard:redirect')


class GymConsoleView(ConsoleAccessMixin, TemplateView):
    template_name = "gym/console.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['school_count'] = School.objects.filter(is_active=True).count()
        ctx['total_members'] = SchoolMember.objects.filter(is_active=True).count()
        ctx['total_volunteers'] = SchoolVolunteer.objects.filter(is_active=True).count()
        ctx['total_disciples'] = SchoolDisciple.objects.count()
        income_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        expense_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, expense_qs)
        ctx['audit_logs'] = AuditLog.objects.filter(scope='gym')[:25]
        return ctx


def _gym_info_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'gym_info')


def _gym_finance_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'gym_finance')


def _gym_schools_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'gym_schools')


def _gym_media_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'gym_media')


@login_required
@user_passes_test(_gym_info_or_super, login_url='/dashboard/redirect/')
def feed_item_create(request):
    if request.method == 'POST':
        form = FeedItemForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.scope = FeedItem.Scope.GYM
            obj.created_by = request.user
            obj.save()
            messages.success(request, f"'{obj.title}' added to the GYM feed.")
            return redirect('gym:info_dashboard')
    else:
        form = FeedItemForm(initial={'published_at': tz.now(), 'expires_at': tz.now() + tz.timedelta(days=14)})
    return render(request, 'gym/feed_item_form.html', {'form': form})


@login_required
@user_passes_test(_gym_schools_or_super, login_url='/dashboard/redirect/')
def school_create(request):
    if request.method == 'POST':
        form = SchoolForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "School added.")
            return redirect('gym:schools_dashboard')
    else:
        form = SchoolForm()
    return render(request, 'gym/school_form.html', {'form': form})


@login_required
@user_passes_test(_gym_schools_or_super, login_url='/dashboard/redirect/')
def school_member_create(request):
    if request.method == 'POST':
        form = SchoolMemberForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{obj.full_name} added at {obj.school.name}.")
            return redirect('gym:schools_dashboard')
    else:
        form = SchoolMemberForm()
    return render(request, 'gym/school_member_form.html', {'form': form})


@login_required
@user_passes_test(_gym_schools_or_super, login_url='/dashboard/redirect/')
def school_volunteer_create(request):
    if request.method == 'POST':
        form = SchoolVolunteerForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{obj.full_name} added as a volunteer at {obj.school.name}.")
            return redirect('gym:schools_dashboard')
    else:
        form = SchoolVolunteerForm()
    return render(request, 'gym/school_volunteer_form.html', {'form': form})


@login_required
@user_passes_test(_gym_schools_or_super, login_url='/dashboard/redirect/')
def school_disciple_create(request):
    if request.method == 'POST':
        form = SchoolDiscipleForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"{obj.full_name} enrolled as a disciple at {obj.school.name}.")
            return redirect('gym:schools_dashboard')
    else:
        form = SchoolDiscipleForm()
    return render(request, 'gym/school_disciple_form.html', {'form': form})


@login_required
@user_passes_test(_gym_media_or_super, login_url='/dashboard/redirect/')
def school_activity_create(request):
    if request.method == 'POST':
        form = SchoolActivityForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"'{obj.title}' recorded at {obj.school.name}.")
            return redirect('gym:media_dashboard')
    else:
        form = SchoolActivityForm()
    return render(request, 'gym/school_activity_form.html', {'form': form})


@login_required
@user_passes_test(_gym_finance_or_super, login_url='/dashboard/redirect/')
def finance_create(request):
    if request.method == 'POST':
        form = GymFinanceForm(request.POST)
        if form.is_valid():
            if request.POST.get('confirm') == '1':
                obj = form.save(commit=False)
                obj.recorded_by = request.user
                obj.save()
                messages.success(request, f"{obj.get_type_display()} of {obj.amount} {obj.currency} recorded.")
                return redirect('gym:finance_dashboard')
            return render(request, 'gym/finance_confirm.html', {'form': form})
    else:
        form = GymFinanceForm()
    return render(request, 'gym/finance_form.html', {'form': form})


@login_required
@user_passes_test(_gym_finance_or_super, login_url='/dashboard/redirect/')
def finance_record_detail(request, pk):
    """Read-only — finance admins can see the full detail of any entry but cannot edit it."""
    record = get_object_or_404(FinanceRecord, pk=pk)
    return render(request, 'gym/finance_detail.html', {'record': record})


@login_required
@user_passes_test(_gym_finance_or_super, login_url='/dashboard/redirect/')
def finance_reports(request):
    qs = FinanceRecord.objects.all()
    return render(request, 'gym/finance_reports.html', {
        'report_sections': [
            ('Daily', period_breakdown(qs, TruncDate, limit=30)),
            ('Weekly', period_breakdown(qs, TruncWeek, limit=12)),
            ('Monthly', period_breakdown(qs, TruncMonth, limit=12)),
            ('Annual', period_breakdown(qs, TruncYear, limit=5)),
        ],
    })


@login_required
@user_passes_test(_gym_finance_or_super, login_url='/dashboard/redirect/')
def finance_report_export(request):
    qs = FinanceRecord.objects.all().order_by('-date')
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="gym_finance_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Currency', 'School', 'Description', 'Recorded By'])
    for r in qs:
        writer.writerow(sanitize_csv_row([
            r.date, r.get_type_display(), r.income_category or r.expense_category or r.other_category_note,
            r.amount, r.currency, r.school.name if r.school else '', r.description,
            r.recorded_by.get_full_name() or r.recorded_by.username if r.recorded_by else '',
        ]))
    return response