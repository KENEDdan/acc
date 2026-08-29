from django.db import models
from django.conf import settings
from .choices import Currency


class Budget(models.Model):
    """A budget request for a specific activity/event, walked through Finance
    Admin -> Superadmin approval. Either reviewer can send it back with a
    comment instead of forwarding/approving; `returned_by` records who sent it
    back so the UI knows whose turn it is to fix and resubmit it."""

    class Scope(models.TextChoices):
        CHURCH = 'church', 'Church (ACC)'
        GYM = 'gym', 'Global Youth Ministry'
        AFF = 'aff', "Apostles' Feet Foundation"

    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted — Awaiting Finance Review'
        FORWARDED = 'forwarded', 'Forwarded to Superadmin'
        RETURNED = 'returned', 'Returned — Needs Changes'
        APPROVED = 'approved', 'Approved'

    class ReturnedBy(models.TextChoices):
        FINANCE = 'finance', 'Finance Admin'
        SUPERADMIN = 'superadmin', 'Superadmin'

    scope = models.CharField(max_length=10, choices=Scope.choices)

    church_activity = models.ForeignKey(
        'church.Activity', on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets'
    )
    gym_activity = models.ForeignKey(
        'gym.SchoolActivity', on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets'
    )
    aff_activity = models.ForeignKey(
        'aff.Activity', on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets'
    )

    title = models.CharField(max_length=200, help_text="Snapshot of the activity/event name at submission time")
    category = models.CharField(max_length=100, help_text="Snapshot of the activity's category at submission time")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.SSP)
    justification = models.TextField(help_text="Why this activity needs this budget")

    status = models.CharField(max_length=15, choices=Status.choices, default=Status.SUBMITTED)
    returned_by = models.CharField(max_length=10, choices=ReturnedBy.choices, blank=True)

    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='budgets_submitted'
    )
    forwarded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets_forwarded'
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='budgets_approved'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def get_activity(self):
        return self.church_activity or self.gym_activity or self.aff_activity

    def finance_role(self):
        return f"{self.scope}_finance"

    def __str__(self):
        return f"{self.title} - {self.amount} {self.currency} ({self.get_status_display()})"


class BudgetComment(models.Model):
    class Action(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        FORWARDED = 'forwarded', 'Forwarded to Superadmin'
        APPROVED = 'approved', 'Approved'
        RETURNED = 'returned', 'Returned'
        RESUBMITTED = 'resubmitted', 'Resubmitted'
        COMMENT = 'comment', 'Comment'

    budget = models.ForeignKey(Budget, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=15, choices=Action.choices, default=Action.COMMENT)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.get_action_display()} on Budget #{self.budget_id}"
