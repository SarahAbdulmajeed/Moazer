from django import forms
from django.contrib.auth import get_user_model
from .models import StudentProfile, ExpertProfile

User = get_user_model()

GENDER_CHOICES = (
    ("male", "male"),
    ("female", "female"),
)


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False)
    password_confirm = forms.CharField(widget=forms.PasswordInput, required=False)
    dob = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}))
    gender = forms.ChoiceField(choices=GENDER_CHOICES, required=False)

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "email",
            "gender",
            "dob",
            "phone",
            "city",
            "bio",
            "profile_picture",
            "password",
            "password_confirm",
        ]

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        if password and password != password_confirm:
            raise forms.ValidationError("Passwords do not match!")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["stage"]


class ExpertProfileForm(forms.ModelForm):
    specialties = forms.MultipleChoiceField(
        choices=ExpertProfile.SPECIALTY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    consultation_types = forms.MultipleChoiceField(
        choices=ExpertProfile.CONSULTATION_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = ExpertProfile
        fields = ["iban", "hourly_price", "specialties", "consultation_types"]
