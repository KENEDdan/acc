from django.views.generic import TemplateView, ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum, Q, Avg, Max
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
from django.core.paginator import Paginator
import csv
import datetime

from django_ratelimit.decorators import ratelimit

from newsfeed.models import FeedItem, FeedItemManager
from finance.utils import currency_breakdown, period_breakdown, sanitize_csv_row
from audit.models import AuditLog
from audit.services import log_action
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect
from .forms import (
    MemberForm, DiscipleshipEnrollmentForm, ChurchFinanceForm, MediaItemForm, LiveServiceForm,
    LibraryResourceForm, BranchForm, PastorElderForm, PrayerRequestForm, PrayerResponseForm, AttendanceRecordForm,
    CounselingRequestForm, CounselingScheduleDateForm, GivingAccountForm, GivingRecordForm, GivingRecordReviewForm,
)
from newsfeed.forms import FeedItemForm
from django.utils import timezone as tz
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.http import HttpResponse
from .id_cards import generate_member_id_card_pdf
from accounts.services import create_member_account, reset_member_password
from notifications.services import notify_role, notify_superadmins, notify_user
from .models import (
    Activity, Member, DiscipleshipEnrollment, MediaItem,
    LibraryResource, AboutUs, FinanceRecord, Branch, LiveService,
    PastorElder, PrayerRequest, AttendanceRecord, CounselingSession,
    GivingAccount, GivingRecord,
)


class ChurchHomeView(TemplateView):
    template_name = "church/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['feed_items'] = FeedItemManager.active(scope=FeedItem.Scope.CHURCH)[:30]
        ctx['live_service'] = LiveService.objects.filter(is_live=True).first()
        ctx['upcoming_activities'] = Activity.objects.filter(is_active=True)[:10]
        return ctx


class AboutUsView(TemplateView):
    template_name = "church/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['about'] = AboutUs.objects.first()
        return ctx


class ActivityListView(ListView):
    model = Activity
    template_name = "church/activities.html"
    context_object_name = "activities"
    queryset = Activity.objects.filter(is_active=True)


class ActivityDetailView(DetailView):
    model = Activity
    template_name = "church/activity_detail.html"
    context_object_name = "activity"


class SermonListView(ListView):
    model = MediaItem
    template_name = "church/media_list.html"
    context_object_name = "media_items"

    def get_queryset(self):
        return MediaItem.objects.filter(media_type=MediaItem.MediaType.SERMON, is_active=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "Sermons"
        return ctx


class TeachingListView(ListView):
    model = MediaItem
    template_name = "church/media_list.html"
    context_object_name = "media_items"

    def get_queryset(self):
        return MediaItem.objects.filter(media_type=MediaItem.MediaType.TEACHING, is_active=True)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['page_title'] = "Teachings"
        return ctx


class LibraryListView(ListView):
    model = LibraryResource
    template_name = "church/library.html"
    context_object_name = "resources"
    queryset = LibraryResource.objects.filter(is_active=True)


class BranchListView(ListView):
    model = Branch
    template_name = "church/branches.html"
    context_object_name = "branches"
    queryset = Branch.objects.filter(is_active=True)


class PastorElderListView(ListView):
    model = PastorElder
    template_name = "church/pastors_elders.html"
    context_object_name = "leaders"
    queryset = PastorElder.objects.filter(is_active=True)


class LiveView(TemplateView):
    template_name = "church/live.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['live_service'] = LiveService.objects.filter(is_live=True).first()
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
    template_name = "church/dashboards/info_dashboard.html"
    allowed_roles = ('church_info',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_items'] = FeedItem.objects.filter(scope=FeedItem.Scope.CHURCH).order_by('-created_at')[:20]
        return ctx


class FinanceDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "church/dashboards/finance_dashboard.html"
    allowed_roles = ('church_finance',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        month_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        qs = FinanceRecord.objects.filter(date__gte=month_start)
        income_qs = qs.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        expense_qs = qs.filter(type=FinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, expense_qs)
        ctx['recent_records'] = FinanceRecord.objects.all()[:20]
        ctx['pending_giving_count'] = GivingRecord.objects.filter(status=GivingRecord.Status.PENDING).count()
        return ctx


class MembershipDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "church/dashboards/membership_dashboard.html"
    allowed_roles = ('church_membership',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['member_count'] = Member.objects.filter(is_active=True).count()
        ctx['branch_count'] = Branch.objects.filter(is_active=True).count()
        ctx['recent_members'] = Member.objects.order_by('-registered_at')[:20]
        ctx['new_prayer_requests'] = PrayerRequest.objects.filter(status=PrayerRequest.Status.SUBMITTED)
        ctx['recent_attendance'] = AttendanceRecord.objects.all()[:5]
        ctx['new_counseling_requests'] = CounselingSession.objects.filter(status=CounselingSession.Status.REQUESTED).count()
        return ctx


class DiscipleshipDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "church/dashboards/discipleship_dashboard.html"
    allowed_roles = ('church_discipleship',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['ongoing_count'] = DiscipleshipEnrollment.objects.filter(status='ongoing').count()
        ctx['completed_count'] = DiscipleshipEnrollment.objects.filter(status='completed').count()
        ctx['enrollments'] = DiscipleshipEnrollment.objects.order_by('-registered_at')[:20]
        return ctx


class MediaDashboardView(RoleDashboardMixin, TemplateView):
    template_name = "church/dashboards/media_dashboard.html"
    allowed_roles = ('church_media',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['sermon_count'] = MediaItem.objects.filter(media_type=MediaItem.MediaType.SERMON).count()
        ctx['teaching_count'] = MediaItem.objects.filter(media_type=MediaItem.MediaType.TEACHING).count()
        ctx['live_service'] = LiveService.objects.filter(is_live=True).first()
        ctx['recent_media'] = MediaItem.objects.all()[:20]
        ctx['recent_library'] = LibraryResource.objects.all()[:20]
        return ctx


class ConsoleAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    ministry_roles = ('church_info', 'church_finance', 'church_membership', 'church_discipleship', 'church_media')

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superadmin() or u.role in self.ministry_roles)

    def handle_no_permission(self):
        from django.shortcuts import redirect
        return redirect('dashboard:redirect')


class ChurchConsoleView(ConsoleAccessMixin, TemplateView):
    template_name = "church/console.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['member_count'] = Member.objects.filter(is_active=True).count()
        ctx['branch_count'] = Branch.objects.filter(is_active=True).count()
        ctx['ongoing_disciples'] = DiscipleshipEnrollment.objects.filter(status='ongoing').count()
        income_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        expense_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.EXPENSE).values('currency').annotate(total=Sum('amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, expense_qs)
        ctx['audit_logs'] = AuditLog.objects.filter(scope='church')[:25]
        return ctx


def _church_membership_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'church_membership')


def _church_discipleship_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'church_discipleship')


def _church_finance_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'church_finance')


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def member_create(request):
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.registered_by = request.user
            obj.save()
            temp_password = create_member_account(obj)
            return render(request, 'church/member_registered.html', {
                'member': obj, 'temp_password': temp_password,
            })
    else:
        form = MemberForm()
    return render(request, 'church/member_form.html', {'form': form})

@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def members_list(request):
    query = request.GET.get('q', '').strip()
    branch_id = request.GET.get('branch', '').strip()
    membership_type = request.GET.get('type', '').strip()

    members = Member.objects.filter(is_active=True).order_by('-registered_at')
    if query:
        members = members.filter(
            Q(full_name__icontains=query) | Q(member_id__icontains=query) | Q(contact_phone__icontains=query)
        )
    if branch_id:
        members = members.filter(branch_id=branch_id)
    if membership_type:
        members = members.filter(membership_type=membership_type)

    paginator = Paginator(members, 25)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'church/members_list.html', {
        'page_obj': page_obj,
        'query': query,
        'branch_id': branch_id,
        'membership_type': membership_type,
        'branches': Branch.objects.filter(is_active=True),
        'membership_types': Member.MembershipType.choices,
    })


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def member_detail(request, pk):
    member = get_object_or_404(Member, pk=pk)
    return render(request, 'church/member_detail.html', {'member': member})


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def member_edit(request, pk):
    member = get_object_or_404(Member, pk=pk)
    if request.method == 'POST':
        form = MemberForm(request.POST, request.FILES, instance=member)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'church', 'Member', obj, action='update')
            messages.success(request, f"{obj.full_name}'s information has been updated.")
            return redirect('church:member_detail', pk=obj.pk)
    else:
        form = MemberForm(instance=member)
    return render(request, 'church/member_form.html', {'form': form, 'member': member, 'is_edit': True})


@login_required
@user_passes_test(_church_discipleship_or_super, login_url='/dashboard/redirect/')
def discipleship_create(request):
    if request.method == 'POST':
        form = DiscipleshipEnrollmentForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.registered_by = request.user
            obj.save()
            messages.success(request, f"{obj.full_name} enrolled in Discipleship Phase {obj.phase_number}.")
            return redirect('church:discipleship_dashboard')
    else:
        form = DiscipleshipEnrollmentForm()
    return render(request, 'church/discipleship_form.html', {'form': form})


@login_required
@user_passes_test(_church_discipleship_or_super, login_url='/dashboard/redirect/')
def discipleship_detail(request, pk):
    enrollment = get_object_or_404(DiscipleshipEnrollment, pk=pk)
    return render(request, 'church/discipleship_detail.html', {'enrollment': enrollment})


@login_required
@user_passes_test(_church_discipleship_or_super, login_url='/dashboard/redirect/')
def discipleship_edit(request, pk):
    enrollment = get_object_or_404(DiscipleshipEnrollment, pk=pk)
    if request.method == 'POST':
        form = DiscipleshipEnrollmentForm(request.POST, instance=enrollment)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'church', 'DiscipleshipEnrollment', obj, action='update')
            messages.success(request, f"{obj.full_name}'s discipleship record has been updated.")
            return redirect('church:discipleship_detail', pk=obj.pk)
    else:
        form = DiscipleshipEnrollmentForm(instance=enrollment)
    return render(request, 'church/discipleship_form.html', {'form': form, 'enrollment': enrollment, 'is_edit': True})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def finance_create(request):
    if request.method == 'POST':
        form = ChurchFinanceForm(request.POST)
        if form.is_valid():
            if request.POST.get('confirm') == '1':
                obj = form.save(commit=False)
                obj.recorded_by = request.user
                obj.save()
                messages.success(request, f"{obj.get_type_display()} of {obj.amount} {obj.currency} recorded.")
                return redirect('church:finance_dashboard')
            return render(request, 'church/finance_confirm.html', {'form': form})
    else:
        form = ChurchFinanceForm()
    return render(request, 'church/finance_form.html', {'form': form})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def finance_record_detail(request, pk):
    """Read-only — finance admins can see the full detail of any entry but cannot edit it."""
    record = get_object_or_404(FinanceRecord, pk=pk)
    return render(request, 'church/finance_detail.html', {'record': record})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def finance_reports(request):
    qs = FinanceRecord.objects.all()
    return render(request, 'church/finance_reports.html', {
        'report_sections': [
            ('Daily', period_breakdown(qs, TruncDate, limit=30)),
            ('Weekly', period_breakdown(qs, TruncWeek, limit=12)),
            ('Monthly', period_breakdown(qs, TruncMonth, limit=12)),
            ('Annual', period_breakdown(qs, TruncYear, limit=5)),
        ],
    })


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def finance_report_export(request):
    """Downloads a CSV of finance records, optionally filtered to a date range."""
    qs = FinanceRecord.objects.all().order_by('-date')
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="church_finance_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Currency', 'Branch', 'Description', 'Recorded By'])
    for r in qs:
        writer.writerow(sanitize_csv_row([
            r.date, r.get_type_display(), r.income_category or r.expense_category or r.other_category_note,
            r.amount, r.currency, r.branch.name if r.branch else '', r.description,
            r.recorded_by.get_full_name() or r.recorded_by.username if r.recorded_by else '',
        ]))
    return response


    # ---------- Giving / Donations ----------

@ratelimit(key='ip', rate='10/h', method='POST', block=True)
def giving_create(request):
    """Public 'Give' page — works for anonymous visitors and, if logged in, registered members alike.
    Shows the active bank/MoMo accounts and lets the giver log what they sent, for Finance to confirm."""
    accounts = GivingAccount.objects.filter(is_active=True)
    if request.method == 'POST':
        form = GivingRecordForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.given_by_user = request.user
                member_profile = getattr(request.user, 'member_profile', None)
                if member_profile:
                    obj.member = member_profile
                    if not obj.giver_name:
                        obj.giver_name = member_profile.full_name
            obj.save()
            notify_role(
                'church_finance',
                f"New giving submitted: {obj.amount} {obj.currency} ({obj.get_purpose_display()}) from {obj.giver_name or 'Anonymous'}.",
                link="/church/dashboard/finance/giving-records/",
            )
            return render(request, 'church/giving_submitted.html', {'giving': obj})
    else:
        form = GivingRecordForm()
    return render(request, 'church/give.html', {'form': form, 'accounts': accounts})


@login_required
def my_giving_history(request):
    """A registered giver's own submissions and their review status."""
    records = GivingRecord.objects.filter(given_by_user=request.user).order_by('-submitted_at')
    return render(request, 'church/my_giving_history.html', {'records': records})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_accounts_list(request):
    accounts = GivingAccount.objects.all()
    return render(request, 'church/giving_accounts_list.html', {'accounts': accounts})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_account_create(request):
    if request.method == 'POST':
        form = GivingAccountForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            log_action(request.user, 'church', 'GivingAccount', obj, action='create')
            messages.success(request, f"'{obj.label}' added to Giving Accounts.")
            return redirect('church:giving_accounts_list')
    else:
        form = GivingAccountForm()
    return render(request, 'church/giving_account_form.html', {'form': form})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_account_edit(request, pk):
    account = get_object_or_404(GivingAccount, pk=pk)
    if request.method == 'POST':
        form = GivingAccountForm(request.POST, instance=account)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            log_action(request.user, 'church', 'GivingAccount', obj, action='update')
            messages.success(request, f"'{obj.label}' updated.")
            return redirect('church:giving_accounts_list')
    else:
        form = GivingAccountForm(instance=account)
    return render(request, 'church/giving_account_form.html', {'form': form, 'account': account, 'is_edit': True})


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_records_list(request):
    status = request.GET.get('status', 'pending')
    records = GivingRecord.objects.all()
    if status in dict(GivingRecord.Status.choices):
        records = records.filter(status=status)
    return render(request, 'church/giving_records_list.html', {
        'records': records, 'status': status, 'review_form': GivingRecordReviewForm(),
    })


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_record_confirm(request, pk):
    record = get_object_or_404(GivingRecord, pk=pk, status=GivingRecord.Status.PENDING)
    if request.method == 'POST':
        category_map = {
            GivingRecord.Purpose.TITHE: FinanceRecord.IncomeCategory.TITHES,
            GivingRecord.Purpose.OFFERTORY: FinanceRecord.IncomeCategory.OFFERTORY,
            GivingRecord.Purpose.DONATION: FinanceRecord.IncomeCategory.DONATION,
            GivingRecord.Purpose.FREE_WILL: FinanceRecord.IncomeCategory.FREE_WILL,
            GivingRecord.Purpose.OTHER: FinanceRecord.IncomeCategory.DONATION,
        }
        description = f"Online giving from {record.giver_name or 'Anonymous'} ({record.get_purpose_display()})"
        if record.transaction_reference:
            description += f" — ref: {record.transaction_reference}"
        finance_record = FinanceRecord.objects.create(
            type=FinanceRecord.Type.INCOME,
            income_category=category_map.get(record.purpose, FinanceRecord.IncomeCategory.DONATION),
            other_category_note=record.get_purpose_display() if record.purpose == GivingRecord.Purpose.OTHER else '',
            amount=record.amount,
            currency=record.currency,
            date=timezone.now().date(),
            description=description,
            recorded_by=request.user,
        )
        record.status = GivingRecord.Status.CONFIRMED
        record.finance_record = finance_record
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()
        if record.given_by_user_id:
            notify_user(
                record.given_by_user,
                f"Thank you! Your giving of {record.amount} {record.currency} has been confirmed.",
                link="/church/give/history/",
            )
        messages.success(request, f"Confirmed and posted {record.amount} {record.currency} to the finance ledger.")
    return redirect('church:giving_records_list')


@login_required
@user_passes_test(_church_finance_or_super, login_url='/dashboard/redirect/')
def giving_record_reject(request, pk):
    record = get_object_or_404(GivingRecord, pk=pk, status=GivingRecord.Status.PENDING)
    if request.method == 'POST':
        form = GivingRecordReviewForm(request.POST, instance=record)
        record = form.save(commit=False)
        record.status = GivingRecord.Status.REJECTED
        record.reviewed_by = request.user
        record.reviewed_at = timezone.now()
        record.save()
        if record.given_by_user_id:
            notify_user(
                record.given_by_user,
                "There was an issue confirming your recent giving submission — please check your giving history for details.",
                link="/church/give/history/",
            )
        messages.success(request, "Giving record rejected.")
    return redirect('church:giving_records_list')


def _church_info_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'church_info')


def _church_media_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'church_media')


@login_required
@user_passes_test(_church_info_or_super, login_url='/dashboard/redirect/')
def feed_item_create(request):
    if request.method == 'POST':
        form = FeedItemForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.scope = FeedItem.Scope.CHURCH
            obj.created_by = request.user
            obj.save()
            messages.success(request, f"'{obj.title}' added to the church feed.")
            return redirect('church:info_dashboard')
    else:
        form = FeedItemForm(initial={
            'published_at': tz.now(),
            'expires_at': tz.now() + tz.timedelta(days=14),
        })
    return render(request, 'church/feed_item_form.html', {'form': form})


@login_required
@user_passes_test(_church_info_or_super, login_url='/dashboard/redirect/')
def feed_item_detail(request, pk):
    item = get_object_or_404(FeedItem, pk=pk, scope=FeedItem.Scope.CHURCH)
    return render(request, 'church/feed_item_detail.html', {'item': item})


@login_required
@user_passes_test(_church_info_or_super, login_url='/dashboard/redirect/')
def feed_item_edit(request, pk):
    item = get_object_or_404(FeedItem, pk=pk, scope=FeedItem.Scope.CHURCH)
    if request.method == 'POST':
        form = FeedItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'church', 'FeedItem', obj, action='update')
            messages.success(request, f"'{obj.title}' updated.")
            return redirect('church:feed_item_detail', pk=obj.pk)
    else:
        form = FeedItemForm(instance=item)
    return render(request, 'church/feed_item_form.html', {'form': form, 'item': item, 'is_edit': True})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def media_item_create(request):
    if request.method == 'POST':
        form = MediaItemForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.uploaded_by = request.user
            obj.save()
            messages.success(request, f"'{obj.title}' added as a {obj.get_media_type_display()}.")
            return redirect('church:media_dashboard')
    else:
        form = MediaItemForm()
    return render(request, 'church/media_item_form.html', {'form': form})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def media_item_detail(request, pk):
    item = get_object_or_404(MediaItem, pk=pk)
    return render(request, 'church/media_item_detail.html', {'item': item})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def media_item_edit(request, pk):
    item = get_object_or_404(MediaItem, pk=pk)
    if request.method == 'POST':
        form = MediaItemForm(request.POST, instance=item)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'church', 'MediaItem', obj, action='update')
            messages.success(request, f"'{obj.title}' updated.")
            return redirect('church:media_item_detail', pk=obj.pk)
    else:
        form = MediaItemForm(instance=item)
    return render(request, 'church/media_item_form.html', {'form': form, 'item': item, 'is_edit': True})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def live_start(request):
    if request.method == 'POST':
        form = LiveServiceForm(request.POST)
        if form.is_valid():
            LiveService.objects.filter(is_live=True).update(is_live=False, ended_at=tz.now())
            obj = form.save(commit=False)
            obj.is_live = True
            obj.started_at = tz.now()
            obj.started_by = request.user
            obj.save()
            messages.success(request, f"Now live on {obj.get_platform_display()}: {obj.title}")
            return redirect('church:media_dashboard')
    else:
        form = LiveServiceForm(initial={'title': 'Live Service'})
    return render(request, 'church/live_form.html', {'form': form})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def live_end(request):
    LiveService.objects.filter(is_live=True).update(is_live=False, ended_at=tz.now())
    messages.success(request, "Live service ended.")
    return redirect('church:media_dashboard')

@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def member_id_card(request, pk):
    member = get_object_or_404(Member, pk=pk)
    verify_url = request.build_absolute_uri(reverse('church:member_verify', args=[member.member_id]))
    buf = generate_member_id_card_pdf(member, verify_url)
    response = HttpResponse(buf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="ACC_ID_{member.member_id}.pdf"'
    return response


def member_verify(request, member_id):
    member = get_object_or_404(Member, member_id=member_id)
    return render(request, 'church/member_verify.html', {'member': member})

@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def library_item_create(request):
    if request.method == 'POST':
        form = LibraryResourceForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.uploaded_by = request.user
            obj.save()
            messages.success(request, f"'{obj.title}' added to the library.")
            return redirect('church:media_dashboard')
    else:
        form = LibraryResourceForm()
    return render(request, 'church/library_item_form.html', {'form': form})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def library_item_detail(request, pk):
    item = get_object_or_404(LibraryResource, pk=pk)
    return render(request, 'church/library_item_detail.html', {'item': item})


@login_required
@user_passes_test(_church_media_or_super, login_url='/dashboard/redirect/')
def library_item_edit(request, pk):
    item = get_object_or_404(LibraryResource, pk=pk)
    if request.method == 'POST':
        form = LibraryResourceForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            obj = form.save()
            log_action(request.user, 'church', 'LibraryResource', obj, action='update')
            messages.success(request, f"'{obj.title}' updated.")
            return redirect('church:library_item_detail', pk=obj.pk)
    else:
        form = LibraryResourceForm(instance=item)
    return render(request, 'church/library_item_form.html', {'form': form, 'item': item, 'is_edit': True})

def _superadmin_only(user):
    return user.is_authenticated and user.is_superadmin()


@login_required
@user_passes_test(_superadmin_only, login_url='/dashboard/redirect/')
def branch_create(request):
    if request.method == 'POST':
        form = BranchForm(request.POST)
        if form.is_valid():
            obj = form.save()
            messages.success(request, f"Branch '{obj.name}' added.")
            return redirect('church:branches')
    else:
        form = BranchForm()
    return render(request, 'church/branch_form.html', {'form': form})


@login_required
@user_passes_test(_superadmin_only, login_url='/dashboard/redirect/')
def pastor_elder_create(request):
    if request.method == 'POST':
        form = PastorElderForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.added_by = request.user
            obj.save()
            messages.success(request, f"{obj.full_name} added to Pastors & Elders.")
            return redirect('church:pastors_elders')
    else:
        form = PastorElderForm()
    return render(request, 'church/pastor_elder_form.html', {'form': form})

@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def member_reset_password(request):
    """Admin-assisted password reset, for members without an email on file
    (or who otherwise can't use the self-service 'Forgot password' flow)."""
    lookup_id = request.GET.get('member_id', '').strip()
    member = Member.objects.filter(member_id__iexact=lookup_id).first() if lookup_id else None
    temp_password = None

    if request.method == 'POST':
        member = get_object_or_404(Member, pk=request.POST.get('member_pk'))
        temp_password = reset_member_password(member)

    return render(request, 'church/member_reset_password.html', {
        'member': member, 'temp_password': temp_password, 'lookup_id': lookup_id,
    })

    # ---------- Prayer Requests ----------

@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def prayer_request_create(request):
    """Public — works for anonymous visitors and, if logged in, registered members alike."""
    if request.method == 'POST':
        form = PrayerRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.submitted_by_user = request.user
                member_profile = getattr(request.user, 'member_profile', None)
                if member_profile:
                    obj.member = member_profile
                    if not obj.submitted_by_name:
                        obj.submitted_by_name = member_profile.full_name
            obj.save()
            notify_role(
                'church_membership',
                f"New prayer request from {obj.submitted_by_name or 'an anonymous visitor'}.",
                link="/church/dashboard/membership/",
            )
            return render(request, 'church/prayer_request_submitted.html', {'prayer_request': obj})
    else:
        form = PrayerRequestForm()
    return render(request, 'church/prayer_request_form.html', {'form': form})


def prayer_request_lookup(request):
    """Public — lets an anonymous submitter check for a response using their reference code."""
    prayer_request = None
    error = None
    code = request.GET.get('code', '').strip().upper()
    if code:
        prayer_request = PrayerRequest.objects.filter(reference_code=code).first()
        if not prayer_request:
            error = "No prayer request found with that reference code."
    return render(request, 'church/prayer_request_lookup.html', {
        'prayer_request': prayer_request, 'code': code, 'error': error,
    })


@login_required
def prayer_request_detail(request, pk):
    pr = get_object_or_404(PrayerRequest, pk=pk)
    is_owner = pr.submitted_by_user_id == request.user.id
    is_staff = request.user.is_superadmin() or request.user.role == 'church_membership'
    if not (is_owner or is_staff):
        return redirect('dashboard:redirect')
    return render(request, 'church/prayer_request_detail.html', {
        'prayer_request': pr, 'is_owner': is_owner, 'is_staff': is_staff,
        'is_superadmin_user': request.user.is_superadmin(),
    })


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def prayer_requests_list(request):
    prayer_requests = PrayerRequest.objects.all()[:100]
    return render(request, 'church/prayer_requests_list.html', {'prayer_requests': prayer_requests})


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def prayer_request_forward(request, pk):
    """Membership Admin reviews a prayer request and forwards it to the superadmin."""
    pr = get_object_or_404(PrayerRequest, pk=pk, status=PrayerRequest.Status.SUBMITTED)
    if request.method == 'POST':
        pr.status = PrayerRequest.Status.FORWARDED
        pr.save()
        notify_superadmins(f"Prayer request {pr.reference_code} was forwarded for your attention.", link="/dashboard/superadmin/")
        messages.success(request, "Prayer request forwarded to the superadmin.")
    return redirect('church:prayer_request_detail', pk=pr.pk)


@login_required
@user_passes_test(_superadmin_only, login_url='/dashboard/redirect/')
def prayer_request_respond(request, pk):
    """Superadmin writes the response; it flows back down to Membership Admin and the submitter."""
    pr = get_object_or_404(PrayerRequest, pk=pk)
    if request.method == 'POST':
        form = PrayerResponseForm(request.POST, instance=pr)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.status = PrayerRequest.Status.RESPONDED
            obj.responded_by = request.user
            obj.responded_at = timezone.now()
            obj.save()
            notify_role('church_membership', f"A response is ready for prayer request {obj.reference_code}.", link=f"/church/prayer-requests/{obj.pk}/")
            if obj.submitted_by_user_id:
                notify_user(obj.submitted_by_user, "You have a response to your prayer request.", link=f"/church/prayer-requests/{obj.pk}/")
            messages.success(request, "Response saved.")
            return redirect('church:prayer_request_detail', pk=obj.pk)
    else:
        form = PrayerResponseForm(instance=pr)
    return render(request, 'church/prayer_request_respond.html', {'form': form, 'prayer_request': pr})


# ---------- Attendance ----------

@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def attendance_create(request):
    if request.method == 'POST':
        form = AttendanceRecordForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.recorded_by = request.user
            obj.save()
            messages.success(request, f"Attendance recorded: {obj.count} on {obj.date}.")
            return redirect('church:attendance_reports')
    else:
        form = AttendanceRecordForm(initial={'date': tz.now().date()})
    return render(request, 'church/attendance_form.html', {'form': form})


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def attendance_reports(request):
    weekly = (AttendanceRecord.objects
              .annotate(period=TruncWeek('date')).values('period')
              .annotate(total=Sum('count'), avg=Avg('count')).order_by('-period')[:12])
    monthly = (AttendanceRecord.objects
               .annotate(period=TruncMonth('date')).values('period')
               .annotate(total=Sum('count'), avg=Avg('count')).order_by('-period')[:12])
    annual = (AttendanceRecord.objects
              .annotate(period=TruncYear('date')).values('period')
              .annotate(total=Sum('count'), avg=Avg('count')).order_by('-period')[:5])
    recent = AttendanceRecord.objects.all()[:15]
    return render(request, 'church/attendance_reports.html', {
        'weekly': weekly, 'monthly': monthly, 'annual': annual, 'recent': recent,
    })


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def attendance_delete(request, pk):
    """Clears a mistaken headcount entry. Membership Admin and the superadmin only."""
    record = get_object_or_404(AttendanceRecord, pk=pk)
    if request.method == 'POST':
        log_action(request.user, 'church', 'AttendanceRecord', record, action='delete')
        record.delete()
        messages.success(request, "Attendance record cleared.")
    return redirect('church:attendance_reports')

    # ---------- Counseling Sessions ----------

@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def counseling_request_create(request):
    """Public — works for anonymous visitors and, if logged in, registered members alike."""
    if request.method == 'POST':
        form = CounselingRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            if request.user.is_authenticated:
                obj.booked_by_user = request.user
                member_profile = getattr(request.user, 'member_profile', None)
                if member_profile:
                    obj.member = member_profile
            obj.save()
            notify_role('church_membership', f"New counseling session request from {obj.full_name}.", link="/church/dashboard/membership/")
            return render(request, 'church/counseling_requested.html', {'session': obj})
    else:
        form = CounselingRequestForm()
    return render(request, 'church/counseling_request_form.html', {'form': form})


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def counseling_requests_list(request):
    requested = CounselingSession.objects.filter(status=CounselingSession.Status.REQUESTED)
    upcoming = CounselingSession.objects.filter(status=CounselingSession.Status.SCHEDULED)
    return render(request, 'church/counseling_requests_list.html', {'requested': requested, 'upcoming': upcoming})


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def counseling_schedule(request, pk):
    """Membership Admin picks a Monday/Wednesday date, then an open hour on that date.
    Already-taken hours are excluded from the choices, and the database's unique
    constraint on scheduled_slot makes a double-booking impossible even under a race."""
    session = get_object_or_404(CounselingSession, pk=pk, status=CounselingSession.Status.REQUESTED)

    chosen_date = None
    available_hours = []
    date_form = CounselingScheduleDateForm(
        request.GET or {'date': session.preferred_date},
    )
    if date_form.is_valid():
        chosen_date = date_form.cleaned_data['date']
        taken_hours = set(
            CounselingSession.objects.filter(scheduled_slot__date=chosen_date)
            .exclude(status=CounselingSession.Status.CANCELLED)
            .values_list('scheduled_slot__hour', flat=True)
        )
        available_hours = [h for h in CounselingSession.VALID_HOURS if h not in taken_hours]

    if request.method == 'POST' and chosen_date:
        hour = request.POST.get('hour')
        try:
            hour = int(hour)
        except (TypeError, ValueError):
            hour = None
        if hour in available_hours:
            naive_slot = datetime.datetime.combine(chosen_date, datetime.time(hour=hour))
            slot = tz.make_aware(naive_slot)
            session.scheduled_slot = slot
            session.status = CounselingSession.Status.SCHEDULED
            session.scheduled_by = request.user
            session.save()
            when_text = slot.strftime('%A, %b %d at %I:%M %p')
            notify_superadmins(f"Counseling session scheduled: {session.full_name} on {when_text}.", link="/church/counseling/queue/")
            if session.booked_by_user_id:
                notify_user(session.booked_by_user, f"Your counseling session is scheduled for {when_text}.", link="/dashboard/member/")
            messages.success(request, f"Scheduled {session.full_name} for {when_text}.")
            return redirect('church:counseling_requests_list')
        messages.error(request, "That hour is no longer available. Please pick another.")

    return render(request, 'church/counseling_schedule.html', {
        'session': session, 'date_form': date_form, 'chosen_date': chosen_date, 'available_hours': available_hours,
    })


@login_required
@user_passes_test(_church_membership_or_super, login_url='/dashboard/redirect/')
def counseling_queue(request):
    """Today's schedule - visible to both Membership Admin and the superadmin (the pastor)."""
    today = tz.now().date()
    todays_sessions = (CounselingSession.objects
                        .filter(scheduled_slot__date=today)
                        .exclude(status=CounselingSession.Status.CANCELLED)
                        .order_by('scheduled_slot'))
    return render(request, 'church/counseling_queue.html', {
        'todays_sessions': todays_sessions, 'today': today,
    })


@login_required
@user_passes_test(_superadmin_only, login_url='/dashboard/redirect/')
def counseling_next(request):
    """The pastor presses Next: completes whoever is current, and calls up the next scheduled hour today."""
    today = tz.now().date()
    if request.method == 'POST':
        current = CounselingSession.objects.filter(scheduled_slot__date=today, status=CounselingSession.Status.CURRENT).first()
        if current:
            current.status = CounselingSession.Status.COMPLETED
            current.save()

        next_session = (CounselingSession.objects
                         .filter(scheduled_slot__date=today, status=CounselingSession.Status.SCHEDULED)
                         .order_by('scheduled_slot').first())
        if next_session:
            next_session.status = CounselingSession.Status.CURRENT
            next_session.save()
            if next_session.booked_by_user_id:
                notify_user(next_session.booked_by_user, "It's your turn now - please head to the pastor's office.", link="/dashboard/member/")
            notify_role(
                'church_membership',
                f"{next_session.full_name} is now being seen by the pastor."
                + ("" if next_session.booked_by_user_id else " No account on file - please help notify them directly."),
                link="/church/counseling/queue/",
            )
            messages.success(request, f"Now seeing: {next_session.full_name}.")
        else:
            messages.info(request, "No more sessions scheduled for today.")
    return redirect('church:counseling_queue')