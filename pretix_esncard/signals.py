from collections import OrderedDict
from django.dispatch import receiver
from pretix.base.signals import register_global_settings
from pretix.presale.signals import question_form_fields_overrides

from pretix_esncard.forms import ESNCardSettingsForm
from pretix_esncard.validation import get_esncard_question, val_esncard


@receiver(question_form_fields_overrides, dispatch_uid="esncard_form_field")
def override_esncard_question(sender, position, request, **kwargs):
    question = get_esncard_question(position)
    if not question:
        return {}

    def validate_esncard_field(esncard_number: str):
        val_esncard(esncard_number, question, sender, position, request)

    return {question.identifier: {"validators": [validate_esncard_field]}}


@receiver(register_global_settings, dispatch_uid="esncard_global_settings")
def global_settings(sender, **kwargs):
    return OrderedDict(
        [
            (
                "esncard_cf_token",
                ESNCardSettingsForm.base_fields["esncard_cf_token"],
            ),
        ]
    )
