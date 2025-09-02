from django import forms
from .models import Plan

class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = ["name", "attempts", "price_sar"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "w-full border rounded p-2"}),
            "attempts": forms.NumberInput(attrs={"class": "w-full border rounded p-2"}),
            "price_sar": forms.NumberInput(attrs={"class": "w-full border rounded p-2"}),
        }
