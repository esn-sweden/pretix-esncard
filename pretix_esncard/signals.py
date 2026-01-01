import logging
from collections import OrderedDict
from collections.abc import Iterable

from django.dispatch import receiver
from pretix.base.models import CartPosition
from pretix.base.services.cart import CartError
from pretix.base.signals import register_global_settings, validate_cart

from pretix_esncard.api import ExternalAPIError
from pretix_esncard.forms import ESNCardSettingsForm
from pretix_esncard.helpers import (
    check_duplicates,
    delete_wrong_answers,
    generate_error_message,
    get_esncard_answers,
    log_card_states,
    populate_cards,
)

logger = logging.getLogger(__name__)


@receiver(validate_cart, dispatch_uid="esncard_validate_cart")
def esncard_validate_cart(positions: Iterable[CartPosition], **kwargs):
    cards = get_esncard_answers(positions)

    try:
        populate_cards(cards)
    except ExternalAPIError as e:
        logger.error("ESNcard validation failed due to API error: %s", e)
        raise CartError(
            "We could not verify your ESNcard due to a temporary service issue. Please try again later."
            "If the problem persists, please contact support@seabattle.se."
        )

    check_duplicates(cards)
    log_card_states(cards)

    error_msg = generate_error_message(cards)

    if error_msg:
        # Post error message (and return to first step of checkout)
        logger.info(error_msg)
        delete_wrong_answers(cards)
        raise CartError(error_msg)


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
