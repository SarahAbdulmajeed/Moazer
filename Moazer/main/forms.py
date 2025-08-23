from django import forms
from django.contrib.auth import get_user_model
from .models import StudentProfile, ExpertProfile

User = get_user_model()


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name","last_name","gender","dob","phone","city","bio","profile_picture"]


class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ["stage"]


class ExpertProfileForm(forms.ModelForm):
    class Meta:
        model = ExpertProfile
        fields = ["iban","hourly_price"]
