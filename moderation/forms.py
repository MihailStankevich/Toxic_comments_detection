# moderation/forms.py
from django import forms
from .models import Owner

class OwnerRegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    
    class Meta:
        model = Owner
        fields = ['username', 'password', 'channel_id']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Owner.objects.filter(username=username).exists():
            raise forms.ValidationError("A user with that email already exists.")
        return username