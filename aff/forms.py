from django import forms
from .models import AssistanceRequest, FinanceRecord, CashReconciliation


class AssistanceRequestForm(forms.ModelForm):
    class Meta:
        model = AssistanceRequest
        exclude = ('status', 'filled_by', 'reviewed_by', 'reviewed_at', 'review_notes', 'disbursed_amount', 'disbursed_at', 'created_at')
        widgets = {
            'request_date': forms.DateInput(attrs={'type': 'date'}),
            'tel': forms.TextInput(attrs={'type': 'tel'}),
            'membership_duration': forms.TextInput(attrs={'placeholder': 'e.g. 4 years'}),
            'salvation_when_where': forms.TextInput(),
            'salvation_experience': forms.Textarea(attrs={'rows': 3}),
            'department_serving': forms.TextInput(),
            'how_church_can_help': forms.Textarea(attrs={'rows': 3, 'placeholder': 'How can the church help, and why?'}),
            'other_need_note': forms.TextInput(),
            'help_directed_other': forms.TextInput(),
        }


class AssistanceReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=[
            ('approved', 'Approve'),
            ('declined', 'Decline'),
            ('info_needed', 'Request More Information'),
        ],
        widget=forms.RadioSelect, label="Decision",
    )
    review_notes = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3}), required=False,
        label="Notes",
        help_text="Shown to the AFF finance admin who submitted this request. Required when declining or requesting more information.",
    )

    def clean(self):
        cleaned_data = super().clean()
        decision = cleaned_data.get('decision')
        review_notes = (cleaned_data.get('review_notes') or '').strip()
        if decision in ('declined', 'info_needed') and not review_notes:
            self.add_error(
                'review_notes',
                "Please add a comment explaining your decision — this is what the AFF finance admin will see."
            )
        cleaned_data['review_notes'] = review_notes
        return cleaned_data


class DisbursementForm(forms.Form):
    disbursed_amount = forms.DecimalField(max_digits=12, decimal_places=2, label="Amount Disbursed")
    disbursed_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), label="Date Disbursed")


class AffFinanceForm(forms.ModelForm):
    class Meta:
        model = FinanceRecord
        exclude = ('recorded_by', 'recorded_at', 'related_request')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CashReconciliationForm(forms.ModelForm):
    class Meta:
        model = CashReconciliation
        exclude = ('recorded_by', 'recorded_at', 'discrepancy')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }