from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from audit.services import log_action
from notifications.services import notify_role, notify_user, notify_superadmins
from .models import Budget, BudgetComment
from .forms import BudgetForm, BudgetActionForm

User = get_user_model()

SUBMITTER_ROLES = (
    'church_info', 'church_membership', 'church_discipleship', 'church_media',
    'gym_info', 'gym_schools', 'gym_media',
    'aff_info',
)
FINANCE_ROLES = ('church_finance', 'gym_finance', 'aff_finance')


def _scope_for_role(role):
    return role.split('_')[0]


def _can_submit(user):
    return user.is_authenticated and user.role in SUBMITTER_ROLES


def _can_review_finance(user):
    return user.is_authenticated and (user.is_superadmin() or user.role in FINANCE_ROLES)


@login_required
@user_passes_test(_can_submit, login_url='/dashboard/redirect/')
def budget_list(request):
    budgets = Budget.objects.filter(submitted_by=request.user)
    return render(request, 'finance/budget_list.html', {'budgets': budgets})


@login_required
@user_passes_test(_can_submit, login_url='/dashboard/redirect/')
def budget_create(request):
    scope = _scope_for_role(request.user.role)
    if request.method == 'POST':
        form = BudgetForm(request.POST, scope=scope)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.submitted_by = request.user
            obj.status = Budget.Status.SUBMITTED
            obj.save()
            BudgetComment.objects.create(budget=obj, author=request.user, action=BudgetComment.Action.SUBMITTED)
            log_action(request.user, scope, 'Budget', obj, action='create', details=f"Submitted for {obj.amount} {obj.currency}")
            notify_role(obj.finance_role(), f"New budget request '{obj.title}' ({obj.amount} {obj.currency}) needs your review.", link=f"/finance/budgets/{obj.pk}/")
            messages.success(request, "Budget request submitted to your Finance Admin for review.")
            return redirect('finance:budget_list')
    else:
        form = BudgetForm(scope=scope)
    return render(request, 'finance/budget_form.html', {'form': form, 'budget': None})


@login_required
def budget_detail(request, pk):
    budget = get_object_or_404(Budget, pk=pk)
    user = request.user
    is_owner = budget.submitted_by_id == user.id
    is_finance = user.role == budget.finance_role()
    is_superadmin = user.is_superadmin()
    if not (is_owner or is_finance or is_superadmin):
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        action = request.POST.get('action')
        form = BudgetActionForm(request.POST)
        message = form.cleaned_data.get('message', '') if form.is_valid() else request.POST.get('message', '')

        can_forward = is_finance and budget.status in (Budget.Status.SUBMITTED, Budget.Status.RETURNED) and (
            budget.status == Budget.Status.SUBMITTED or budget.returned_by == Budget.ReturnedBy.SUPERADMIN
        )
        can_return_by_finance = is_finance and budget.status == Budget.Status.SUBMITTED
        can_return_by_superadmin = is_superadmin and budget.status == Budget.Status.FORWARDED
        can_approve = is_superadmin and budget.status == Budget.Status.FORWARDED

        if action == 'forward' and can_forward:
            was_returned = budget.status == Budget.Status.RETURNED
            budget.status = Budget.Status.FORWARDED
            budget.returned_by = ''
            budget.forwarded_by = user
            budget.save()
            BudgetComment.objects.create(
                budget=budget, author=user, message=message,
                action=BudgetComment.Action.RESUBMITTED if was_returned else BudgetComment.Action.FORWARDED,
            )
            log_action(user, budget.scope, 'Budget', budget, action='update', details='Forwarded to superadmin')
            notify_superadmins(f"Budget request '{budget.title}' was forwarded for your approval.", link=f"/finance/budgets/{budget.pk}/")
            messages.success(request, "Forwarded to the superadmin for approval.")

        elif action == 'return' and (can_return_by_finance or can_return_by_superadmin):
            if not message.strip():
                messages.error(request, "Please add a comment explaining what needs to change.")
                return redirect('finance:budget_detail', pk=pk)
            budget.status = Budget.Status.RETURNED
            budget.returned_by = Budget.ReturnedBy.SUPERADMIN if is_superadmin else Budget.ReturnedBy.FINANCE
            budget.save()
            BudgetComment.objects.create(budget=budget, author=user, message=message, action=BudgetComment.Action.RETURNED)
            log_action(user, budget.scope, 'Budget', budget, action='update', details='Returned with a comment')
            if is_superadmin:
                notify_role(budget.finance_role(), f"Your budget request '{budget.title}' was returned by the superadmin — see comments.", link=f"/finance/budgets/{budget.pk}/")
            else:
                notify_user(budget.submitted_by, f"Your budget request '{budget.title}' was returned by Finance — see comments.", link=f"/finance/budgets/{budget.pk}/")
            messages.success(request, "Sent back with your comment.")

        elif action == 'approve' and can_approve:
            budget.status = Budget.Status.APPROVED
            budget.approved_by = user
            budget.save()
            BudgetComment.objects.create(budget=budget, author=user, message=message, action=BudgetComment.Action.APPROVED)
            log_action(user, budget.scope, 'Budget', budget, action='update', details='Approved')
            if budget.submitted_by_id:
                notify_user(budget.submitted_by, f"Your budget request '{budget.title}' was approved.", link=f"/finance/budgets/{budget.pk}/")
            notify_role(budget.finance_role(), f"Budget request '{budget.title}' was approved by the superadmin.", link=f"/finance/budgets/{budget.pk}/")
            messages.success(request, "Budget approved.")

        elif action == 'comment' and (is_owner or is_finance or is_superadmin):
            if not message.strip():
                messages.error(request, "Comment can't be empty.")
                return redirect('finance:budget_detail', pk=pk)
            BudgetComment.objects.create(budget=budget, author=user, message=message, action=BudgetComment.Action.COMMENT)
            messages.success(request, "Comment added.")

        else:
            messages.error(request, "That action isn't available for this request right now.")

        return redirect('finance:budget_detail', pk=pk)

    can_edit = (
        (is_owner and budget.status == Budget.Status.RETURNED and budget.returned_by == Budget.ReturnedBy.FINANCE) or
        (is_finance and budget.status == Budget.Status.RETURNED and budget.returned_by == Budget.ReturnedBy.SUPERADMIN)
    )
    context = {
        'budget': budget,
        'is_owner': is_owner,
        'is_finance': is_finance,
        'is_superadmin': is_superadmin,
        'can_forward': is_finance and (budget.status == Budget.Status.SUBMITTED or (budget.status == Budget.Status.RETURNED and budget.returned_by == Budget.ReturnedBy.SUPERADMIN)),
        'can_return': (is_finance and budget.status == Budget.Status.SUBMITTED) or (is_superadmin and budget.status == Budget.Status.FORWARDED),
        'can_approve': is_superadmin and budget.status == Budget.Status.FORWARDED,
        'can_edit': can_edit,
        'action_form': BudgetActionForm(),
    }
    return render(request, 'finance/budget_detail.html', context)


@login_required
def budget_edit(request, pk):
    budget = get_object_or_404(Budget, pk=pk, status=Budget.Status.RETURNED)
    user = request.user
    is_owner_turn = budget.submitted_by_id == user.id and budget.returned_by == Budget.ReturnedBy.FINANCE
    is_finance_turn = user.role == budget.finance_role() and budget.returned_by == Budget.ReturnedBy.SUPERADMIN
    if not (is_owner_turn or is_finance_turn):
        return redirect('dashboard:redirect')

    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, scope=budget.scope)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.returned_by = ''
            if is_owner_turn:
                obj.status = Budget.Status.SUBMITTED
                target_msg = f"'{obj.title}' was updated and resubmitted for your review."
                obj.save()
                BudgetComment.objects.create(budget=obj, author=user, action=BudgetComment.Action.RESUBMITTED)
                notify_role(obj.finance_role(), target_msg, link=f"/finance/budgets/{obj.pk}/")
            else:
                obj.status = Budget.Status.FORWARDED
                obj.forwarded_by = user
                obj.save()
                BudgetComment.objects.create(budget=obj, author=user, action=BudgetComment.Action.RESUBMITTED)
                notify_superadmins(f"'{obj.title}' was updated and resubmitted for your approval.", link=f"/finance/budgets/{obj.pk}/")
            log_action(user, obj.scope, 'Budget', obj, action='update', details='Resubmitted after changes')
            messages.success(request, "Budget updated and resubmitted.")
            return redirect('finance:budget_detail', pk=obj.pk)
    else:
        form = BudgetForm(instance=budget, scope=budget.scope)
    return render(request, 'finance/budget_form.html', {'form': form, 'budget': budget})


@login_required
@user_passes_test(_can_review_finance, login_url='/dashboard/redirect/')
def budget_queue_finance(request):
    scope = _scope_for_role(request.user.role) if not request.user.is_superadmin() else request.GET.get('scope', 'church')
    budgets = Budget.objects.filter(scope=scope).exclude(status=Budget.Status.APPROVED)
    return render(request, 'finance/budget_queue.html', {
        'budgets': budgets, 'queue_title': f"{scope.title()} Budget Approvals", 'is_finance_queue': True,
    })


@login_required
@user_passes_test(lambda u: u.is_authenticated and u.is_superadmin(), login_url='/dashboard/redirect/')
def budget_queue_superadmin(request):
    budgets = Budget.objects.filter(status=Budget.Status.FORWARDED)
    return render(request, 'finance/budget_queue.html', {
        'budgets': budgets, 'queue_title': "Budget Requests Awaiting Your Approval", 'is_finance_queue': False,
    })
