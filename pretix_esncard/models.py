from dataclasses import dataclass
from typing import Optional

from pretix.base.models import CartPosition, QuestionAnswer


@dataclass
class ESNCardEntry:
    position: CartPosition
    answer: QuestionAnswer
    card_number: str
    name: str
    status: Optional[str] = None
    expiration_date: Optional[str] = None
    duplicate: bool = False
    raw_api_data: Optional[dict] = None
