from django import forms
from .models import FeedItem


class FeedItemForm(forms.ModelForm):
    class Meta:
        model = FeedItem
        exclude = ('scope', 'slug', 'is_pinned', 'created_by', 'created_at', 'updated_at')
        widgets = {
            'summary': forms.TextInput(attrs={'maxlength': 300, 'placeholder': 'Short teaser shown on the feed card'}),
            'body': forms.Textarea(attrs={'rows': 6}),
            'event_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'published_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'expires_at': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('is_featured') and not cleaned_data.get('expires_at'):
            self.add_error('expires_at', "Required unless this item is marked as Featured (kept indefinitely).")
        return cleaned_data