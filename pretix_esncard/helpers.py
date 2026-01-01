import logging
from collections import Counter

from pretix_esncard.api import fetch_card
from pretix_esncard.models import ESNCardEntry

logger = logging.getLogger(__name__)


def get_esncard_answers(**kwargs) -> list[ESNCardEntry]:
    """Returns all the ESNcard answers for the current order

    For each position, checks for answers which have the identifier 'esncard'."""
    entries = []
    for _, position in enumerate(kwargs["positions"]):
        for answer in position.answers.all():
            if answer.question.identifier == "esncard":
                name = position.attendee_name
                card_number = str(answer).strip().upper()
                entry = ESNCardEntry(
                    position, answer=answer, card_number=card_number, name=name
                )
                entries.append(entry)
    return entries


def populate_cards(cards: list[ESNCardEntry]):
    """Call the ESNcard API and populate the ESNCardEntry with this information

    The statuses can be active, expired or available (not registered)
    """
    for card in cards:
        data = fetch_card(card.card_number)
        if data:
            card.status = data["status"]
            card.expiration_date = data["expiration-date"]
            card.raw_api_data = data
        else:
            card.status = "not found"


def check_duplicates(cards: list[ESNCardEntry]):
    """Sets duplicate = True to entries that have the same card_number

    Per ESN Sea Battle policy, each participant must have their own ESNcard to get a discount
    """
    counts = Counter(c.card_number for c in cards)
    for card in cards:
        card.duplicate = counts[card.card_number] > 1


def delete_wrong_answers(cards: list[ESNCardEntry]):
    """Delete ESNcard answers if not valid in order to allow new attempt"""
    for card in cards:
        if card.status != "active":
            card.answer.delete()


def log_card_states(cards: list[ESNCardEntry]):
    for card in cards:
        logger.debug(
            "Name: %s, ESNcard number: %s, Status: %s",
            card.name,
            card.card_number,
            card.status,
        )


def generate_error_message(cards: list[ESNCardEntry]) -> str:
    """Build an error message from a list of card entries

    Returns one concatenated string with all the errors found and appends any valid ESNcards in the order.
    Returns '' if no errors are found.
    """
    # Create status lists (bridge to keep the code below working for new ESNCardEntry class)
    empty_cards = [c for c in cards if c.status == "not found"]
    expired = [c for c in cards if c.status == "expired"]
    available = [c for c in cards if c.status == "available"]
    active = [c for c in cards if c.status == "active"]
    invalid = [
        c
        for c in cards
        if c.status not in ("available", "expired", "not found", "active")
    ]
    duplicates = [c for c in cards if c.duplicate]

    error_msg = ""
    # If there are card numbers not returning a JSON response (typo)
    if len(empty_cards) == 1:
        card = empty_cards.pop()
        error_msg = (
            error_msg
            + f"The following ESNcard does not exist: {card.card_number} ({card.name}). Please double check the ESNcard numbers for typos!"
        )
    elif len(empty_cards) > 1:
        card = empty_cards.pop()
        msg = f"The following ESNcards don't exist: {card.card_number} ({card.name})"
        while len(empty_cards) > 0:
            card = empty_cards.pop()
            msg = msg + f", {card.card_number} ({card.name})"
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
            f"The following ESNcard: {card.card_number} ({card.name}), expired on {card.expiration_date}. "
            "You can purchase a new ESNcard from your ESN section."
        )
    elif len(expired) > 1:
        card = expired.pop()
        msg = f"The following ESNcards have expired: {card.card_number} ({card.name})"
        while len(expired) > 0:
            card = expired.pop()
            msg = msg + f", {card.card_number} ({card.name})"
        error_msg = (
            error_msg + msg + ". You can purchase a new ESNcard from your ESN section."
        )
    # If there are unregistered card numbers in the cart
    if len(available) == 1:
        card = available.pop()
        error_msg = error_msg + (
            f"The following ESNcard has not been registered yet: {card.card_number} ({card.name}). "
            "Please add the card to your ESNcard account on https://esncard.org."
        )
    elif len(available) > 1:
        card = available.pop()
        msg = f"The following ESNcards have not been registered yet: {card.card_number} ({card.name})"
        while len(available) > 0:
            card = available.pop()
            msg = msg + f", {card.card_number} ({card.name})"
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
            + f"The following ESNcard is invalid: {card.card_number} ({card.name}). Contact us at support@seabattle.se for more information."
        )
    elif len(invalid) > 1:
        card = invalid.pop()
        msg = f"The following ESNcards are invalid: {card.card_number} ({card.name})"
        while len(invalid) > 0:
            card = invalid.pop()
            msg = msg + f", {card.card_number} ({card.name})"
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
                + f"The following ESNcard is valid: {card.card_number} ({card.name})."
            )
        elif len(active) > 1:
            card = active.pop()
            msg = f"The following ESNcards are valid: {card.card_number} ({card.name})"
            while len(active) > 0:
                card = active.pop()
                msg = msg + f", {card.card_number} ({card.name})"
            error_msg = error_msg + msg + "."
    return error_msg
