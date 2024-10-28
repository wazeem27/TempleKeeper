from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate


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