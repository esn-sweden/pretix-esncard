from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ESNCardEntry:
    position: Any
    answer: Any
    card_number: str
    name: str
    status: Optional[str] = None
    expiration_date: Optional[str] = None
    duplicate: bool = False
    raw_api_data: Optional[dict] = None
