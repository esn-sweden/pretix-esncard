import logging
from django.core.exceptions import ValidationError
from django.http import HttpRequest
from django.utils.formats import localize
from django.utils.translation import gettext_lazy as _
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


def is_duplicate(
    card_num: str,
    question: Question,
    position: CartPosition | OrderPosition,
    request: HttpRequest,
) -> bool:

    positions = get_siblings(position)
    if not positions:
        return False

    return any(
        get_answer_from_post_or_db(question, pos, request) == card_num
        for pos in positions
    )


def get_siblings(
    position: CartPosition | OrderPosition,
) -> list[CartPosition | OrderPosition]:
    # During checkout
    if isinstance(position, CartPosition):
        return list(
            CartPosition.objects.filter(
                event=position.event, cart_id=position.cart_id
            ).exclude(pk=position.pk)
        )

    # When editing an existing order
    elif isinstance(position, OrderPosition):
        return list(position.order.positions.exclude(pk=position.pk))

    else:
        logger.warning(
            "Pretix signal returned unexpected position type: %s",
            type(position).__name__,
        )

        return []


def get_answer_from_post_or_db(
    question: Question, pos: CartPosition | OrderPosition, request: HttpRequest
) -> str | None:
    field_name = f"{pos.id}-question_{question.id}"
    post_answer = request.POST.get(field_name)
    if post_answer:
        return normalize_input(post_answer)

    db_answer = pos.answers.filter(question=question).first()
    if db_answer:
        return normalize_input(db_answer.answer)

    return None


def normalize_input(esncard_number: str | None) -> str:
    if not esncard_number:
        return ""
    return esncard_number.strip().replace(" ", "").upper()


def get_contact_email(event: Event) -> str:
    return (
        event.settings.get("contact_mail")
        or event.organizer.settings.get("contact_mail")
        or _("the organizer")
    )


def get_esncard_question(position: CartPosition | OrderPosition) -> Question | None:
    return position.item.questions.filter(identifier="esncard").first()
