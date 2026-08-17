from django import forms
from .models import (
    Member, DiscipleshipEnrollment, FinanceRecord, MediaItem, LiveService, LibraryResource, Branch,
    PastorElder, PrayerRequest, AttendanceRecord, CounselingSession, GivingAccount, GivingRecord,
)


class MemberForm(forms.ModelForm):
    class Meta:
        model = Member
        exclude = ('member_id', 'registered_by', 'registered_at', 'is_active', 'user')
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
            'salvation_when': forms.TextInput(attrs={'placeholder': 'e.g. 2019, at a crusade'}),
            'salvation_meaning': forms.Textarea(attrs={'rows': 3}),
            'salvation_story': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Who was there, what happened...'}),
            'health_status': forms.Textarea(attrs={'rows': 2}),
            'reason_to_join': forms.Textarea(attrs={'rows': 3}),
            'talents_gifts': forms.Textarea(attrs={'rows': 2}),
            'prior_duration': forms.TextInput(attrs={'placeholder': 'e.g. 3 years'}),
        }


class DiscipleshipEnrollmentForm(forms.ModelForm):
    class Meta:
        model = DiscipleshipEnrollment
        exclude = ('registered_by', 'registered_at', 'end_date')
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
            'salvation_meaning': forms.Textarea(attrs={'rows': 3}),
            'salvation_story': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Who was there, what happened...'}),
            'health_status': forms.Textarea(attrs={'rows': 2}),
            'reason_to_join': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Why do they want to go through discipleship?'}),
            'talents_gifts': forms.Textarea(attrs={'rows': 2}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }


class ChurchFinanceForm(forms.ModelForm):
    class Meta:
        model = FinanceRecord
        exclude = ('recorded_by', 'recorded_at')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class MediaItemForm(forms.ModelForm):
    class Meta:
        model = MediaItem
        exclude = ('uploaded_by', 'published_at')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class LiveServiceForm(forms.ModelForm):
    class Meta:
        model = LiveService
        fields = ('platform', 'stream_url', 'title')


class LibraryResourceForm(forms.ModelForm):
    class Meta:
        model = LibraryResource
        exclude = ('uploaded_by', 'uploaded_at')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'A short summary of the book, like a back-cover blurb.'}),
        }


class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        exclude = ('is_active',)
        widgets = {
            'established_date': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
            'history': forms.Textarea(attrs={'rows': 4, 'placeholder': "A brief history of how this branch was founded"}),
        }
        labels = {
            'leader_name': 'Pastor in Charge / Elder',
            'disciples_count': 'Number of Disciples',
        }


class PastorElderForm(forms.ModelForm):
    class Meta:
        model = PastorElder
        exclude = ('added_by', 'added_at', 'is_active')
        widgets = {
            'biography': forms.Textarea(attrs={'rows': 5, 'placeholder': 'A brief professional biography'}),
            'phone_number': forms.TextInput(attrs={'type': 'tel'}),
            'role_title_other': forms.TextInput(attrs={'placeholder': "Only if 'Other' is selected above"}),
        }


class PrayerRequestForm(forms.ModelForm):
    class Meta:
        model = PrayerRequest
        fields = ('submitted_by_name', 'contact_phone', 'request_text', 'is_urgent')
        widgets = {
            'submitted_by_name': forms.TextInput(attrs={'placeholder': 'Optional - leave blank to stay anonymous'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Optional - if you would like someone to follow up'}),
            'request_text': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Share what you would like us to pray for...'}),
        }


class PrayerResponseForm(forms.ModelForm):
    class Meta:
        model = PrayerRequest
        fields = ('response_text',)
        widgets = {
            'response_text': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Write your response...'}),
        }


class AttendanceRecordForm(forms.ModelForm):
    class Meta:
        model = AttendanceRecord
        exclude = ('recorded_by', 'recorded_at')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.TextInput(attrs={'placeholder': "e.g. 'Easter Sunday', 'combined service'"}),
        }


class CounselingRequestForm(forms.ModelForm):
    class Meta:
        model = CounselingSession
        fields = ('full_name', 'contact_phone', 'topic', 'preferred_date')
        widgets = {
            'preferred_date': forms.DateInput(attrs={'type': 'date'}),
            'topic': forms.TextInput(attrs={'placeholder': "Optional - general topic only, e.g. 'marriage', 'grief'"}),
        }
        labels = {
            'preferred_date': 'Preferred Date',
        }
        help_texts = {
            'preferred_date': "Sessions run Mondays and Wednesdays, 8:00 AM - 4:00 PM. We'll confirm an exact hour.",
        }


class GivingAccountForm(forms.ModelForm):
    class Meta:
        model = GivingAccount
        exclude = ('updated_by', 'updated_at', 'created_at')
        widgets = {
            'instructions': forms.Textarea(attrs={'rows': 3, 'placeholder': "Optional note for givers, e.g. what reference to use"}),
            'momo_number': forms.TextInput(attrs={'type': 'tel'}),
        }


class GivingRecordForm(forms.ModelForm):
    class Meta:
        model = GivingRecord
        fields = (
            'giver_name', 'contact_phone', 'contact_email', 'giving_account', 'purpose',
            'amount', 'currency', 'transaction_reference', 'proof_of_payment', 'message',
        )
        widgets = {
            'giver_name': forms.TextInput(attrs={'placeholder': 'Optional — leave blank to give anonymously'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel', 'placeholder': 'Optional'}),
            'transaction_reference': forms.TextInput(attrs={'placeholder': 'Optional — deposit slip / MoMo transaction ID'}),
            'message': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Optional note to the church...'}),
        }
        labels = {
            'giving_account': 'Account You Sent To',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['giving_account'].queryset = GivingAccount.objects.filter(is_active=True)
        self.fields['giving_account'].required = False


class GivingRecordReviewForm(forms.ModelForm):
    class Meta:
        model = GivingRecord
        fields = ('review_note',)
        widgets = {
            'review_note': forms.TextInput(attrs={'placeholder': 'Optional note, e.g. reason for rejecting'}),
        }


class CounselingScheduleDateForm(forms.Form):
    date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text="Sessions run Mondays and Wednesdays only.",
    )

    def clean_date(self):
        date = self.cleaned_data['date']
        if date.weekday() not in CounselingSession.VALID_WEEKDAYS:
            raise forms.ValidationError("Counseling sessions are only available on Mondays and Wednesdays.")
        return date