from django import forms

from .input_validation import sanitize_user_input, validate_username_input


class UsernameForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Username"}
        ),
    )

    def clean_username(self):
        """
        Validate and sanitize username input using security-focused validation.
        """
        username = self.cleaned_data.get("username", "").strip()

        # Sanitize input to prevent injection attacks
        username = sanitize_user_input(username, max_length=150)

        # Validate username format and security
        is_valid, error_message = validate_username_input(username)

        if not is_valid:
            raise forms.ValidationError(error_message)

        return username
