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