import logging
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from pretix.base.models import CartPosition, OrderPosition, Question

from pretix_esncard.api import ExternalAPIError, fetch_card
from pretix_esncard.models import CardStatus

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
        esncard = fetch_card(esncard_number)
    except ExternalAPIError:
        raise ValidationError(
            "Verification is temporarily unavailable. Please try again later. If the issue persists, contact support@seabattle.se."
        )

    if not esncard:
        raise ValidationError(
            "Couldn't find an ESNcard with this number, please check for typos."
        )

    match esncard.status:
        case CardStatus.ACTIVE:
            return
        case CardStatus.AVAILABLE:
            raise ValidationError(
                "The ESNcard is not registered, please register on esncard.org. "
                "If you recently registered your card, it may take a few hours before it's updated in our system."
            )
        case CardStatus.EXPIRED:
            raise ValidationError(f"The ESNcard expired on {esncard.expiration_date}")


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

    if positions.count() == 0:
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
            logger.debug("Error getting POST data")
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
