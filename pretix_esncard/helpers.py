import logging
from collections import Counter
from collections.abc import Iterable

from pretix.base.models import CartPosition

from pretix_esncard.api import fetch_card
from pretix_esncard.models import ESNCardEntry

logger = logging.getLogger(__name__)


def get_esncard_answers(positions: Iterable[CartPosition]) -> list[ESNCardEntry]:
    """Returns all the ESNcard answers for the current order

    For each position, checks for answers which have the identifier 'esncard'."""
    entries = []
    for position in positions:
        # Note: Static type checking does not work here but you can see the attributes of a position here:
        # https://docs.pretix.eu/dev/api/resources/carts.html#cart-position-resource
        for answer in position.answers.all():  # type: ignore
            if answer.question.identifier == "esncard":
                name = position.attendee_name or ""
                card_number = answer.answer.strip().upper()
                entry = ESNCardEntry(
                    position,
                    answer=answer,
                    card_number=card_number,
                    name=name,
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
    """Returns a concatenated string of all validation errors.

    Returns "" if no errors are found.
    """
    status_msgs = {
        "not found": "not found – check for typos.",
        "available": "not registered – register at esncard.org.",
        "expired": "expired on {date} – contact your local ESN section to get a new card.",
        "other": "is invalid – contact support@seabattle.se",
    }

    msgs = []
    duplicates = set()
    for card in cards:
        info = f"ESNcard for {card.name} ({card.card_number}): "
        msg = status_msgs.get(card.status, status_msgs["other"])
        if "{date}" in msg:
            msg = msg.format(date=card.expiration_date)
        msgs.append(info + msg)

        if card.duplicate:
            duplicates.add(card.card_number)

    if duplicates:
        nums = ", ".join(duplicates)
        msgs.append(
            f"Duplicated ESNcards: {nums} – each person must have a unique ESNcard."
        )
    return " ".join(msgs)
