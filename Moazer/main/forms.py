from django import forms
from .models import User, StudentProfile, ExpertProfile

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'gender', 'dob',
                  'phone', 'city', 'bio', 'profile_picture']

class StudentProfileForm(forms.ModelForm):
    class Meta:
        model = StudentProfile
        fields = ['stage']

class ExpertProfileForm(forms.ModelForm):
    class Meta:
        model = ExpertProfile
        fields = ['iban', 'hourly_price']
