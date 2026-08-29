from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from core.models import SiteContact

User = get_user_model()


class AboutUsForm(forms.Form):
    content = forms.CharField(widget=forms.Textarea(attrs={'rows': 14}), label="About Us Content")


class SiteContactForm(forms.ModelForm):
    class Meta:
        model = SiteContact
        exclude = ('updated_by', 'updated_at')
        widgets = {
            'phone_primary': forms.TextInput(attrs={'type': 'tel'}),
            'phone_secondary': forms.TextInput(attrs={'type': 'tel'}),
            'address': forms.Textarea(attrs={'rows': 3}),
        }


class AdminAccountCreateForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'phone_number', 'role')


class AdminAccountEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'phone_number', 'role', 'is_active')
        widgets = {
            'phone_number': forms.TextInput(attrs={'type': 'tel'}),
        }