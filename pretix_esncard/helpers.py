import requests

API_URL = "https://esncard.org/services/1.0/card.json?code="


def get_esncard_answers(**kwargs):
    fields = []
    for _, position in enumerate(kwargs["positions"]):
        for answer in position.answers.all():
            if answer.question.identifier == "esncard":
                fields.append((position, answer))
    return fields


def get_cards(answers):
    esncards = []
    empty_cards = []
    for position, answer in answers:
        card_number = str(answer).strip().upper()
        card = fetch_card(card_number)
        if not card:
            card = {"code": card_number, "name": position.attendee_name}
            empty_cards.append(card)
        else:
            card["name"] = position.attendee_name
            esncards.append(card)
    return esncards, empty_cards


def fetch_card(card_number):
    url = API_URL + card_number
    response = requests.get(url).json()
    if len(response) == 1:
        response = response.pop()
    return response


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


def delete_wrong_answers(answers, expired, available, invalid, empty_cards, duplicates):
    """Delete ESNcard answers if not valid in order to allow new attempt"""
    for _, answer in answers:
        card_number = str(answer).strip().upper()
        if (
            card_number
            in [i["code"] for i in expired]
            + [i["code"] for i in available]
            + [i["code"] for i in invalid]
            + [i["code"] for i in empty_cards]
            + duplicates
        ):
            answer.delete()


def log_card_states(
    logger, esncards, empty_cards, active, expired, available, invalid, duplicates
):
    logger.debug(f"ESNcards: {esncards}")
    logger.debug(f"Empty cards: {empty_cards}")
    logger.debug(f"Duplicates: {duplicates}")
    logger.debug(f"Active: {active}")
    logger.debug(f"Expired: {expired}")
    logger.debug(f"Available: {available}")
    logger.debug(f"Invalid: {invalid}")


def generate_error_message(
    expired, available, invalid, empty_cards, duplicates, active
):
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
