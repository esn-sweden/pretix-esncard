import logging

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from pretix.base.models import CartPosition, OrderPosition, Question

from pretix_esncard.api import ExternalAPIError, fetch_card

logger = logging.getLogger(__name__)


def val_esncard(
    esncard_number: str,
    question: Question,
    position: CartPosition | OrderPosition,
    request: HttpRequest,
):
    if not esncard_number:
        return

    if is_duplicate(esncard_number, question, position, request):
        raise ValidationError(
            "Duplicate number. Each person must have a unique ESNcard."
        )

    try:
        data = fetch_card(esncard_number)
    except ExternalAPIError:
        raise ValidationError(
            "Verification is temporarily unavailable. Please try again later. If the issue persists, contact support@seabattle.se"
        )

    if not data:
        raise ValidationError(
            "Couldn't find an ESNcard with this number, please check for typos."
        )

    status = data.get("status")
    match status:
        case "active":
            return
        case "available":
            raise ValidationError(
                "The ESNcard is not registered, please register on esncard.org. "
                "If you recently registered your card, it may take take a few hours before it's updated in the systems"
            )
        case "expired":
            raise ValidationError(
                f"The ESNcard expired on {data.get('expiration-date', '?')}"
            )
        case _:
            raise ValidationError(
                "ESNcard validation failed, please contact support@seabattle.se"
            )


def get_esncard_from_post(
    question: Question, pos: CartPosition | OrderPosition, request: HttpRequest
):
    field_name = f"{pos.id}-question_{question.id}"
    field = request.POST.get(field_name)
    if field:
        return field
    else:
        logger.warning(
            "Could not get esncard field from POST. Tried to get: %s From: %s",
            field_name,
            request.POST,
        )
    return request.POST.get(field_name)


def is_duplicate(
    card_num: str,
    question: Question,
    position: CartPosition | OrderPosition,
    request: HttpRequest,
) -> bool:
    card_num = card_num.strip().upper()

    # Case 1: Checkout flow → CartPosition
    if isinstance(position, CartPosition):
        positions = CartPosition.objects.filter(
            event=position.event, cart_id=position.cart_id
        ).exclude(pk=position.pk)

    # Case 2: Editing an existing order → OrderPosition
    elif isinstance(position, OrderPosition):
        positions = position.order.positions.exclude(pk=position.pk)

    # Fallback (should never happen)
    else:
        logger.warning(
            "Pretix signal returned a position that was neither CartPosition nor OrderPosition"
        )
        return False

    if positions.count() < 1:
        return False

    related = []
    for pos in positions:
        logger.debug(position.attendee_name)
        # Get new values from POST as otherwise you will compare to the existing data in the db which may cause errors
        # if the answers have been modified
        new_val = get_esncard_from_post(question, pos, request)
        if new_val:
            related.append(new_val.strip().upper())
        else:
            logger.debug("Didn't get post data")
            for answer in pos.answers.all():  # type: ignore
                if answer.question.identifier == "esncard":
                    related.append(answer.answer.strip().upper())

    return card_num in related


def get_esncard_question(position: CartPosition | OrderPosition) -> Question | None:
    for question in position.item.questions.all():
        if question.identifier == "esncard":
            return question
    return None


def log_val_err(
    esncard_number: str, position: CartPosition | OrderPosition, e: ValidationError
):
    logger.info(
        "ESNcard validation failed. Name: %s, ESNcard number: %s, Error: %s",
        position.attendee_name,
        esncard_number,
        str(e),
    )
