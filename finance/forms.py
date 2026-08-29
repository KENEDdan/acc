from django import forms
from .models import Budget

SCOPE_ACTIVITY_FIELD = {
    Budget.Scope.CHURCH: 'church_activity',
    Budget.Scope.GYM: 'gym_activity',
    Budget.Scope.AFF: 'aff_activity',
}


def _activity_queryset(scope):
    if scope == Budget.Scope.CHURCH:
        from church.models import Activity
        return Activity.objects.filter(is_active=True)
    if scope == Budget.Scope.GYM:
        from gym.models import SchoolActivity
        return SchoolActivity.objects.all()
    from aff.models import Activity
    return Activity.objects.filter(is_active=True)


class BudgetForm(forms.ModelForm):
    """The category admin's budget planner form. The activity choice field is
    swapped in for the current user's scope in __init__; `title`/`category`
    are auto-filled from the chosen activity on save (not user-editable —
    this is what makes the budget's category 'based on the activities')."""

    activity = forms.ModelChoiceField(queryset=None, label="Activity / Event")

    class Meta:
        model = Budget
        fields = ('amount', 'currency', 'justification')
        widgets = {
            'justification': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Why does this activity need this budget?'}),
        }

    def __init__(self, *args, scope=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.scope = scope or (self.instance.scope if self.instance and self.instance.pk else None)
        self.activity_field_name = SCOPE_ACTIVITY_FIELD.get(self.scope)
        self.fields['activity'].queryset = _activity_queryset(self.scope) if self.scope else _activity_queryset(Budget.Scope.CHURCH)
        if self.instance and self.instance.pk:
            self.fields['activity'].initial = self.instance.get_activity()

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.scope = self.scope
        activity = self.cleaned_data['activity']
        obj.church_activity = None
        obj.gym_activity = None
        obj.aff_activity = None
        setattr(obj, self.activity_field_name, activity)
        obj.title = getattr(activity, 'name', None) or getattr(activity, 'title', '')
        obj.category = activity.get_category_display()
        if commit:
            obj.save()
        return obj


class BudgetActionForm(forms.Form):
    message = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False, label="Comment")
