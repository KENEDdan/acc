from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Sum
from django.db.models.functions import TruncDate, TruncWeek, TruncMonth, TruncYear
from django.utils import timezone
import csv
from django.http import HttpResponse

from newsfeed.models import FeedItem, FeedItemManager
from finance.utils import currency_breakdown, period_breakdown, sanitize_csv_row
from finance.models import Budget
from audit.models import AuditLog
from audit.services import log_action
from notifications.services import notify_user, notify_superadmins, notify_role
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .forms import AssistanceRequestForm, AssistanceReviewForm, DisbursementForm, AffFinanceForm, CashReconciliationForm
from django.utils import timezone as tz
from newsfeed.forms import FeedItemForm
from newsfeed.models import FeedItem as FeedItemModel
from .models import AssistanceRequest, AboutUs, FinanceRecord, CashReconciliation


class AffHomeView(TemplateView):
    template_name = "aff/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['feed_items'] = FeedItemManager.active(scope=FeedItem.Scope.AFF)[:30]
        return ctx


class AffAboutUsView(TemplateView):
    template_name = "aff/about.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['about'] = AboutUs.objects.first()
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
    template_name = "aff/dashboards/info_dashboard.html"
    allowed_roles = ('aff_info',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['recent_items'] = FeedItem.objects.filter(scope=FeedItem.Scope.AFF).order_by('-created_at')[:20]
        return ctx


class FinanceDashboardView(RoleDashboardMixin, TemplateView):
    """Handles requests, approval status visibility, and cash reconciliation."""
    template_name = "aff/dashboards/finance_dashboard.html"
    allowed_roles = ('aff_finance',)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        income_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        disbursed_qs = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.DISBURSED).values('currency').annotate(total=Sum('disbursed_amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, disbursed_qs)
        ctx['submitted_requests'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.SUBMITTED)
        ctx['pending_requests'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.PENDING)
        ctx['approved_requests'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.APPROVED)
        ctx['declined_requests'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.DECLINED)
        ctx['info_needed_requests'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.INFO_NEEDED)
        ctx['all_requests'] = AssistanceRequest.objects.all()[:20]
        ctx['recent_reconciliations'] = CashReconciliation.objects.all()[:10]
        ctx['pending_budget_count'] = Budget.objects.filter(scope='aff').exclude(status=Budget.Status.APPROVED).count()
        return ctx


class ConsoleAccessMixin(LoginRequiredMixin, UserPassesTestMixin):
    ministry_roles = ('aff_info', 'aff_finance')

    def test_func(self):
        u = self.request.user
        return u.is_authenticated and (u.is_superadmin() or u.role in self.ministry_roles)

    def handle_no_permission(self):
        from django.shortcuts import redirect
        return redirect('dashboard:redirect')


class AffConsoleView(ConsoleAccessMixin, TemplateView):
    template_name = "aff/console.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        income_qs = FinanceRecord.objects.filter(type=FinanceRecord.Type.INCOME).values('currency').annotate(total=Sum('amount'))
        disbursed_qs = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.DISBURSED).values('currency').annotate(total=Sum('disbursed_amount'))
        ctx['finance_breakdown'] = currency_breakdown(income_qs, disbursed_qs)
        ctx['pending_count'] = AssistanceRequest.objects.filter(status=AssistanceRequest.Status.PENDING).count()
        ctx['audit_logs'] = AuditLog.objects.filter(scope='aff')[:25]
        return ctx


def _aff_finance_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'aff_finance')


def _superadmin_only(user):
    return user.is_authenticated and user.is_superadmin()


def _can_submit_request(user):
    return user.is_authenticated and (user.is_superadmin() or user.role in ('aff_finance', 'member'))


@login_required
@user_passes_test(_can_submit_request, login_url='/dashboard/redirect/')
def request_create(request):
    if request.method == 'POST':
        form = AssistanceRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.filled_by = request.user
            if request.user.role == 'member':
                obj.status = AssistanceRequest.Status.SUBMITTED
                obj.save()
                notify_role('aff_finance', f"New AFF request from {obj.full_name} needs your review.", link=f"/aff/requests/{obj.pk}/")
                messages.success(request, "Your request has been submitted to the AFF office for review.")
                return redirect('dashboard:member')
            obj.status = AssistanceRequest.Status.PENDING
            obj.save()
            messages.success(request, f"Assistance request for {obj.full_name} submitted for superadmin approval.")
            return redirect('aff:finance_dashboard')
    else:
        form = AssistanceRequestForm()
    return render(request, 'aff/request_form.html', {'form': form})


@login_required
def request_detail(request, pk):
    """Visible to AFF finance/superadmin (any request), or to the member/admin who submitted it (their own only)."""
    req = get_object_or_404(AssistanceRequest, pk=pk)
    is_owner = req.filled_by_id == request.user.id
    is_staff_reviewer = request.user.is_superadmin() or request.user.role == 'aff_finance'
    if not (is_owner or is_staff_reviewer):
        return redirect('dashboard:redirect')
    return render(request, 'aff/request_detail.html', {'req': req, 'is_owner': is_owner, 'is_staff_reviewer': is_staff_reviewer})


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def request_forward(request, pk):
    """AFF finance admin reviews a member's self-submitted request and forwards it to the superadmin."""
    req = get_object_or_404(AssistanceRequest, pk=pk)
    if req.status != AssistanceRequest.Status.SUBMITTED:
        messages.info(request, f"This request is no longer awaiting forwarding (currently: {req.get_status_display()}).")
        return redirect('aff:request_detail', pk=req.pk)
    if request.method == 'POST':
        req.status = AssistanceRequest.Status.PENDING
        req.save()
        log_action(request.user, 'aff', 'AssistanceRequest', req, action='update', details='Forwarded to superadmin for review')
        notify_superadmins(f"AFF request from {req.full_name} was forwarded for your review.", link="/dashboard/superadmin/")
        if req.filled_by_id:
            notify_user(req.filled_by, "Your AFF request has been forwarded to the superadmin for review.", link=f"/aff/requests/{req.pk}/")
        messages.success(request, f"Request from {req.full_name} forwarded to the superadmin.")
    return redirect('aff:request_detail', pk=req.pk)


@login_required
@user_passes_test(_superadmin_only, login_url='/dashboard/redirect/')
def request_review(request, pk):
    req = get_object_or_404(AssistanceRequest, pk=pk)
    if request.method == 'POST':
        form = AssistanceReviewForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            req.status = decision
            req.review_notes = form.cleaned_data['review_notes']
            req.reviewed_by = request.user
            req.reviewed_at = timezone.now()
            req.save()

            if req.filled_by_id:
                if decision == AssistanceRequest.Status.DECLINED:
                    msg = f"Your AFF request for {req.full_name} was declined. Tap to see the reason."
                elif decision == AssistanceRequest.Status.INFO_NEEDED:
                    msg = f"More information is needed on the AFF request for {req.full_name}."
                else:
                    msg = f"Your AFF request for {req.full_name} was approved."
                notify_user(req.filled_by, msg, link=f"/aff/requests/{req.pk}/")

            messages.success(request, f"Request from {req.full_name} marked as {req.get_status_display()}.")
            return redirect('dashboard:superadmin')
    else:
        form = AssistanceReviewForm()
    return render(request, 'aff/request_review.html', {'form': form, 'req': req})


@login_required
def request_resubmit(request, pk):
    """Lets whoever submitted the request (member or AFF admin) update and resend it once info_needed."""
    req = get_object_or_404(AssistanceRequest, pk=pk, status=AssistanceRequest.Status.INFO_NEEDED)
    is_owner = req.filled_by_id == request.user.id
    is_staff_reviewer = request.user.is_superadmin() or request.user.role == 'aff_finance'
    if not (is_owner or is_staff_reviewer):
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = AssistanceRequestForm(request.POST, instance=req)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.status = AssistanceRequest.Status.PENDING
            obj.save()
            log_action(request.user, 'aff', 'AssistanceRequest', obj, action='update', details='Resubmitted with additional information')
            notify_superadmins(
                f"{obj.full_name}'s AFF request was updated with more information and needs review again.",
                link="/dashboard/superadmin/",
            )
            messages.success(request, f"Request for {obj.full_name} resubmitted for review.")
            if request.user.role == 'member':
                return redirect('dashboard:member')
            return redirect('aff:finance_dashboard')
    else:
        form = AssistanceRequestForm(instance=req)
    return render(request, 'aff/request_resubmit.html', {'form': form, 'req': req})


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def request_disburse(request, pk):
    req = get_object_or_404(AssistanceRequest, pk=pk, status=AssistanceRequest.Status.APPROVED)
    if request.method == 'POST':
        form = DisbursementForm(request.POST)
        if form.is_valid():
            req.disbursed_amount = form.cleaned_data['disbursed_amount']
            req.disbursed_at = timezone.now()
            req.status = AssistanceRequest.Status.DISBURSED
            req.save()
            FinanceRecord.objects.create(
                type=FinanceRecord.Type.EXPENSE, amount=req.disbursed_amount, currency=req.currency,
                date=form.cleaned_data['disbursed_date'], description=f"Disbursement to {req.full_name}",
                related_request=req, recorded_by=request.user,
            )
            messages.success(request, f"Disbursement of {req.disbursed_amount} {req.currency} recorded for {req.full_name}.")
            return redirect('aff:finance_dashboard')
    else:
        form = DisbursementForm(initial={'disbursed_amount': req.amount_requested, 'disbursed_date': timezone.now().date()})
    return render(request, 'aff/request_disburse.html', {'form': form, 'req': req})


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def finance_record_create(request):
    if request.method == 'POST':
        form = AffFinanceForm(request.POST)
        if form.is_valid():
            if request.POST.get('confirm') == '1':
                obj = form.save(commit=False)
                obj.recorded_by = request.user
                obj.save()
                messages.success(request, "Finance record saved.")
                return redirect('aff:finance_dashboard')
            return render(request, 'aff/finance_confirm.html', {'form': form})
    else:
        form = AffFinanceForm()
    return render(request, 'aff/finance_form.html', {'form': form})


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def finance_record_detail(request, pk):
    """Read-only — finance admins can see the full detail of any entry but cannot edit it."""
    record = get_object_or_404(FinanceRecord, pk=pk)
    return render(request, 'aff/finance_detail.html', {'record': record})


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def finance_reports(request):
    qs = FinanceRecord.objects.all()
    return render(request, 'aff/finance_reports.html', {
        'report_sections': [
            ('Daily', period_breakdown(qs, TruncDate, limit=30)),
            ('Weekly', period_breakdown(qs, TruncWeek, limit=12)),
            ('Monthly', period_breakdown(qs, TruncMonth, limit=12)),
            ('Annual', period_breakdown(qs, TruncYear, limit=5)),
        ],
    })


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def finance_report_export(request):
    qs = FinanceRecord.objects.all().order_by('-date')
    start = request.GET.get('start')
    end = request.GET.get('end')
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="aff_finance_report.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Category', 'Amount', 'Currency', 'Related Request', 'Description', 'Recorded By'])
    for r in qs:
        writer.writerow(sanitize_csv_row([
            r.date, r.get_type_display(), r.income_category or r.other_category_note,
            r.amount, r.currency, r.related_request.full_name if r.related_request else '', r.description,
            r.recorded_by.get_full_name() or r.recorded_by.username if r.recorded_by else '',
        ]))
    return response


@login_required
@user_passes_test(_aff_finance_or_super, login_url='/dashboard/redirect/')
def reconciliation_create(request):
    if request.method == 'POST':
        form = CashReconciliationForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.recorded_by = request.user
            obj.save()
            messages.success(request, "Cash reconciliation recorded.")
            return redirect('aff:finance_dashboard')
    else:
        form = CashReconciliationForm()
    return render(request, 'aff/reconciliation_form.html', {'form': form})


def _aff_info_or_super(user):
    return user.is_authenticated and (user.is_superadmin() or user.role == 'aff_info')


@login_required
@user_passes_test(_aff_info_or_super, login_url='/dashboard/redirect/')
def feed_item_create(request):
    if request.method == 'POST':
        form = FeedItemForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.scope = FeedItemModel.Scope.AFF
            obj.created_by = request.user
            obj.save()
            messages.success(request, f"'{obj.title}' added to the AFF feed.")
            return redirect('aff:info_dashboard')
    else:
        form = FeedItemForm(initial={'published_at': tz.now(), 'expires_at': tz.now() + tz.timedelta(days=14)})
    return render(request, 'aff/feed_item_form.html', {'form': form})