import logging

from django.dispatch import receiver
from pretix.base.services.cart import CartError
from pretix.base.signals import validate_cart

from pretix_esncard.helpers import (
    check_duplicates,
    delete_wrong_answers,
    generate_error_message,
    get_esncard_answers,
    log_card_states,
    populate_cards,
)


@receiver(validate_cart, dispatch_uid="pretix_esncard_validate_cart")
def esncard_validate_cart(**kwargs):
    logger = logging.getLogger(__name__)

    cards = get_esncard_answers(**kwargs)

    populate_cards(cards)
    check_duplicates(cards)
    log_card_states(logger, cards)
    delete_wrong_answers(cards)

    error_msg = generate_error_message(cards)

    if error_msg:
        logger.info(error_msg)
        raise CartError(
            error_msg
        )  # Post error message (and return to first step of checkout)
