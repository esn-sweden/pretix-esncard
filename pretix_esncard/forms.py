from django import forms
from pretix.base.forms import SettingsForm


class ESNCardSettingsForm(SettingsForm):
    esncard_cf_token = forms.CharField(
        required=False,
        label="ESNcard API Cloudflare token",
        widget=forms.PasswordInput(render_value=True),
        help_text="Used to bypass Cloudflare bot measures",
    )
