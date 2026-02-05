from django import forms
from django.utils.translation import gettext_lazy as _
from pretix.base.forms import SettingsForm


class ESNCardSettingsForm(SettingsForm):
    esncard_cf_token = forms.CharField(
        label=_("ESNcard API Cloudflare token"),
        help_text=_("Used to bypass Cloudflare bot measures"),
        required=False,
        widget=forms.PasswordInput(render_value=True),
    )
