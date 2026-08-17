from django import forms
from .models import School, SchoolMember, SchoolVolunteer, SchoolDisciple, SchoolActivity, FinanceRecord


class SchoolForm(forms.ModelForm):
    class Meta:
        model = School
        fields = '__all__'
        widgets = {
            'joined_date': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
        }


class SchoolMemberForm(forms.ModelForm):
    class Meta:
        model = SchoolMember
        fields = '__all__'
        widgets = {
            'joined_date': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
        }


class SchoolVolunteerForm(forms.ModelForm):
    class Meta:
        model = SchoolVolunteer
        fields = '__all__'
        widgets = {
            'joined_date': forms.DateInput(attrs={'type': 'date'}),
            'contact_phone': forms.TextInput(attrs={'type': 'tel'}),
        }


class SchoolDiscipleForm(forms.ModelForm):
    class Meta:
        model = SchoolDisciple
        fields = '__all__'
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
        }


class SchoolActivityForm(forms.ModelForm):
    class Meta:
        model = SchoolActivity
        fields = '__all__'
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class GymFinanceForm(forms.ModelForm):
    class Meta:
        model = FinanceRecord
        exclude = ('recorded_by', 'recorded_at')
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }