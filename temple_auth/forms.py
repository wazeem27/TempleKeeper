from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from temple_auth.models import Temple
from django.contrib.auth.models import User


class CustomAuthenticationForm(AuthenticationForm):
    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        # Check if both username and password are provided
        if not username or not password:
            raise forms.ValidationError(
                "Please enter both username and password.",
                code='empty_fields',
            )

        # Authenticate the user
        user = authenticate(self.request, username=username, password=password)

        # If user is None, raise a custom invalid login error
        if user is None:
            raise forms.ValidationError(
                "Invalid username or password.",
                code='invalid_login',
            )

        return self.cleaned_data


class TempleCreateForm(forms.ModelForm):
    class Meta:
        model = Temple
        fields = [
            'temple_name', 'temple_place', 'temple_short_name',
            'temple_bill_title', 'temple_bill_mid', 'temple_bill_footer'
        ]

    def clean_name(self):
        name = self.cleaned_data.get('temple_name')
        if not name:
            raise forms.ValidationError("temple_name is required.")
        return name



class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "username", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})