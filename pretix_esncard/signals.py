import logging
import requests
from django.dispatch import receiver
from pretix.base.services.cart import CartError
from pretix.base.signals import validate_cart


@receiver(validate_cart, dispatch_uid="pretix_esncard_validate_cart")
def esncard_validate_cart(sender, **kwargs):
    logger = logging.getLogger(__name__)

    logger.debug(type(sender))
    logger.debug(sender.__dict__.keys())
    logger.debug(kwargs)
    logger.debug(kwargs["positions"])

    esncards = []
    empty_cards = []

    for index, position in enumerate(kwargs["positions"]):
        for answer in position.answers.all():
            logger.debug("Answer keys:")
            logger.debug(answer.__dict__.keys())
            logger.debug(dir(answer))

            logger.debug(str(position.answers.all()))
            if answer.question.identifier == "esncard":
                card_number = str(answer).upper()
                url = "https://esncard.org/services/1.0/card.json?code=" + card_number
                response = requests.get(url).json()
                if len(response) == 1:
                    response = response.pop()
                logger.debug(response)
                logger.debug(type(response))
                if not response:  # I.e., if the list response is empty
                    card = {"code": card_number, "name": position.attendee_name}
                    empty_cards.append(card)
                else:
                    logger.debug(position.attendee_name)
                    response["name"] = position.attendee_name
                    esncards.append(response)

    logger.info("ESNcards:")
    logger.info(esncards)
    logger.info("Empty cards:")
    logger.info(empty_cards)

    duplicates = check_duplicates(esncards)
    logger.info("Duplicates:")
    logger.info(duplicates)

    active, expired, available, invalid = check_status(esncards)
    logger.info("Active:")
    logger.info(active)
    logger.info("Expired:")
    logger.info(expired)
    logger.info("Available")
    logger.info(available)
    logger.info("Invalid:")
    logger.info(invalid)

    # Delete ESNcard answers if not valid in order to allow new attempt
    for index, position in enumerate(kwargs["positions"]):
        for answer in position.answers.all():
            if answer.question.identifier == "esncard":
                card_number = str(answer).upper()
                logger.debug(f"Card number for deletion check: {card_number}")
                codes_to_delete = (
                    [i["code"] for i in expired]
                    + [i["code"] for i in available]
                    + [i["code"] for i in invalid]
                    + [i["code"] for i in empty_cards]
                    + duplicates
                )
                logger.debug(f"List of card numbers to delete: {codes_to_delete}")
                if (
                    card_number
                    in [i["code"] for i in expired]
                    + [i["code"] for i in available]
                    + [i["code"] for i in invalid]
                    + [i["code"] for i in empty_cards]
                    + duplicates
                ):
                    answer.delete()

    # Generate error message
    error_msg = ""
    # If there are card numbers not returning a JSON response (typo)
    if len(empty_cards) == 1:
        card = empty_cards.pop()
        error_msg = (
            error_msg
            + f"The following ESNcard does not exist: {card['code']} ({card['name']}). Please double check the ESNcard numbers for typos!"
        )
    elif len(empty_cards) > 1:
        card = empty_cards.pop()
        msg = f"The following ESNcards don't exist: {card['code']} ({card['name']})"
        while len(empty_cards) > 0:
            card = empty_cards.pop()
            msg = msg + f", {card['code']} ({card['name']})"
        error_msg = (
            error_msg + msg + ". Please double check the ESNcard numbers for typos!"
        )
    # If there are duplicate card numbers in the card
    if len(duplicates) == 1:
        code = duplicates.pop()
        error_msg = (
            error_msg
            + f"The following ESNcard number was used more than once: {code}. Note that the ESNcard discount is personal!"
        )
    elif len(duplicates) > 1:
        code = duplicates.pop()
        msg = f"The following ESNcard numbers were used more than once: {code}"
        while len(empty_cards) > 0:
            code = duplicates.pop()
            msg = msg + f", {code}"
        error_msg = error_msg + msg + ". Note that the ESNcard discount is personal!"
    # If there are expired card numbers in the cart
    if len(expired) == 1:
        card = expired.pop()
        error_msg = error_msg + (
            f"The following ESNcard: {card['code']} ({card['name']}), expired on {card['expiration-date']}. "
            "You can purchase a new ESNcard from your ESN section."
        )
    elif len(expired) > 1:
        card = expired.pop()
        msg = f"The following ESNcards have expired: {card['code']} ({card['name']})"
        while len(expired) > 0:
            card = expired.pop()
            msg = msg + f", {card['code']} ({card['name']})"
        error_msg = (
            error_msg + msg + ". You can purchase a new ESNcard from your ESN section."
        )
    # If there are unregistered card numbers in the cart
    if len(available) == 1:
        card = available.pop()
        error_msg = error_msg + (
            f"The following ESNcard has not been registered yet: {card['code']} ({card['name']}). "
            "Please add the card to your ESNcard account on https://esncard.org."
        )
    elif len(available) > 1:
        card = available.pop()
        msg = f"The following ESNcards have not been registered yet: {card['code']} ({card['name']})"
        while len(available) > 0:
            card = available.pop()
            msg = msg + f", {card['code']} ({card['name']})"
        error_msg = (
            error_msg
            + msg
            + ". Please add the card to your ESNcard account on https://esncard.org."
        )
    # If there are card numbers that for some other reason are not valid
    if len(invalid) == 1:
        card = invalid.pop()
        error_msg = (
            error_msg
            + f"The following ESNcard is invalid: {card['code']} ({card['name']}). Contact us at support@seabattle.se for more information."
        )
    elif len(invalid) > 1:
        card = invalid.pop()
        msg = f"The following ESNcards are invalid: {card['code']} ({card['name']})"
        while len(invalid) > 0:
            card = invalid.pop()
            msg = msg + f", {card['code']} ({card['name']})"
        error_msg = (
            error_msg
            + msg
            + ". Contact us at support@seabattle.se for more information."
        )
    # If there are any invalid ESNcards in the cart, append at the end any other card numbers that may still be valid
    if error_msg != "":
        if len(active) == 1:
            card = active.pop()
            error_msg = (
                error_msg
                + f"The following ESNcard is valid: {card['code']} ({card['name']})."
            )
        elif len(active) > 1:
            card = active.pop()
            msg = f"The following ESNcards are valid: {card['code']} ({card['name']})"
            while len(active) > 0:
                card = active.pop()
                msg = msg + f", {card['code']} ({card['name']})"
            error_msg = error_msg + msg + "."
        # Post error message (and return to first step of checkout)
        logger.debug(error_msg)
        raise CartError(error_msg)


def check_duplicates(esncards):
    codes = [i["code"] for i in esncards]
    temp = []
    duplicates = []
    for i in codes:
        if i not in temp:
            temp.append(i)
        else:
            duplicates.append(i)
    return duplicates


def check_status(esncards):
    active = []
    expired = []
    available = []
    invalid = []
    for i in esncards:
        if i["status"] == "active":
            active.append(i)
        elif i["status"] == "expired":
            expired.append(i)
        elif i["status"] == "available":
            available.append(i)
        else:
            invalid.append(i)
    return active, expired, available, invalid
