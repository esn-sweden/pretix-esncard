import logging
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.translation import gettext_lazy as _
from django.utils.formats import localize
from pretix.base.models import CartPosition, Event, OrderPosition, Question

from pretix_esncard.api import ExternalAPIError, fetch_card
from pretix_esncard.models import CardStatus

logger = logging.getLogger(__name__)


def val_esncard(
    esncard_number: str,
    question: Question,
    event: Event,
    position: CartPosition | OrderPosition,
    request: HttpRequest,
):
    esncard_number = normalize_input(esncard_number)

    if not esncard_number:
        return

    if is_duplicate(esncard_number, question, position, request):
        raise ValidationError(
            _("Duplicate number. Each person must have a unique ESNcard.")
        )

    try:
        esncard = fetch_card(esncard_number)
    except ExternalAPIError:
        raise ValidationError(
            _(
                "Verification is temporarily unavailable. Please try again later. If the issue persists, contact %(email)s."
            )
            % {"email": get_contact_email(event)}
        )

    if not esncard:
        raise ValidationError(
            _("Couldn't find an ESNcard with this number, please check for typos.")
        )

    match esncard.status:
        case CardStatus.ACTIVE:
            return
        case CardStatus.AVAILABLE:
            raise ValidationError(
                _(
                    "The ESNcard is not registered, please register on esncard.org. "
                    "If you recently registered your card, it may take a few hours before it's updated in our system."
                )
            )
        case CardStatus.EXPIRED:
            raise ValidationError(
                _(
                    "The ESNcard expired on %(exp_date)s"
                    % {"exp_date": localize(esncard.expiration_date)}
                )
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
            "Could not get esncard field from POST. Tried to get: %s. POST keys: %s",
            field_name,
            list(request.POST.keys()),
        )

    return request.POST.get(field_name)


def is_duplicate(
    card_num: str,
    question: Question,
    position: CartPosition | OrderPosition,
    request: HttpRequest,
) -> bool:

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
            "Pretix signal returned unexpected position type: %s",
            type(position).__name__,
        )

        return False

    if positions.count() == 0:
        return False

    related = []
    for pos in positions:
        # Get new values from POST as otherwise you will compare to the existing data in the db which may cause errors
        # if the answers have been modified
        new_val = get_esncard_from_post(question, pos, request)
        if new_val:
            related.append(normalize_input(new_val))
        else:
            for answer in pos.answers.all():  # type: ignore
                if answer.question.identifier == "esncard":
                    related.append(normalize_input(answer.answer))

    return card_num in related


def get_esncard_question(position: CartPosition | OrderPosition) -> Question | None:
    for question in position.item.questions.all():
        if question.identifier == "esncard":
            return question
    return None


def normalize_input(esncard_number: str) -> str:
    return esncard_number.strip().replace(" ", "").upper()


def get_contact_email(event: Event) -> str:
    return (
        event.settings.get("contact_mail")
        or event.organizer.settings.get("contact_mail")
        or "the organizer"
    )
