from django import forms


class JoinHouseholdForm(forms.Form):
    invite_code = forms.CharField(max_length=8, label="Invite code")
    display_name = forms.CharField(max_length=100, label="Your name")

    def clean_invite_code(self):
        return self.cleaned_data["invite_code"].strip().upper()

    def clean_display_name(self):
        display_name = self.cleaned_data["display_name"].strip()
        if not display_name:
            raise forms.ValidationError("Enter a name.")
        return display_name
