import logging

from django.dispatch import receiver
from pretix.base.services.cart import CartError
from pretix.base.signals import validate_cart

from pretix_esncard.api import ExternalAPIError
from pretix_esncard.helpers import (
    check_duplicates,
    delete_wrong_answers,
    generate_error_message,
    get_esncard_answers,
    log_card_states,
    populate_cards,
)

logger = logging.getLogger(__name__)


@receiver(validate_cart, dispatch_uid="pretix_esncard_validate_cart")
def esncard_validate_cart(**kwargs):
    cards = get_esncard_answers(**kwargs)

    try:
        populate_cards(cards)
    except ExternalAPIError:
        logger.error("ESNcard validation failed due to API error")
        raise CartError(
            "We could not verify your ESNcard due to a temporary service issue. Please try again later. If the problem persists, please contact support@seabattle.se."
        )

    check_duplicates(cards)
    log_card_states(cards)
    delete_wrong_answers(cards)

    error_msg = generate_error_message(cards)

    if error_msg:
        # Post error message (and return to first step of checkout)
        logger.info(error_msg)
        raise CartError(error_msg)
