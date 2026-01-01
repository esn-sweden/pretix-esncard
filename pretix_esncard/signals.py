import logging

from django.dispatch import receiver
from pretix.base.services.cart import CartError
from pretix.base.signals import validate_cart

from pretix_esncard.helpers import (
    check_duplicates,
    check_status,
    delete_wrong_answers,
    generate_error_message,
    get_cards,
    get_esncard_answers,
    log_card_states,
)


@receiver(validate_cart, dispatch_uid="pretix_esncard_validate_cart")
def esncard_validate_cart(**kwargs):
    logger = logging.getLogger(__name__)

    answers = get_esncard_answers(**kwargs)
    esncards, empty_cards = get_cards(answers)

    duplicates = check_duplicates(esncards)
    active, expired, available, invalid = check_status(esncards)

    log_card_states(
        logger, esncards, empty_cards, active, expired, available, invalid, duplicates
    )

    delete_wrong_answers(
        answers,
        expired,
        available,
        invalid,
        empty_cards,
        duplicates,
    )
    error_msg = generate_error_message(
        expired, available, invalid, empty_cards, duplicates, active
    )
    if error_msg:
        logger.info(error_msg)
        raise CartError(
            error_msg
        )  # Post error message (and return to first step of checkout)
