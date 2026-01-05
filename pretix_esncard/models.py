from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, RootModel, field_validator


class CardStatus(Enum):
    ACTIVE = "active"
    AVAILABLE = "available"
    EXPIRED = "expired"


class ESNCard(BaseModel):
    code: str
    tid: int
    expiration_date: date | None = Field(alias="expiration-date")
    status: CardStatus
    section_code: str | None = Field(alias="section-code")
    activation_date: date | None = Field(alias="activation date")

    @field_validator(
        "expiration_date", "section_code", "activation_date", mode="before"
    )
    def normalize_empty(cls, value: str):
        if isinstance(value, list):
            if len(value) == 0:
                return None
            if len(value) > 1:
                raise ValueError(f"Expected at most one value, got {value}")
            value = value[0]

        if value == "":
            return None

        return value


class ESNCardResponse(RootModel):
    root: list[ESNCard] = Field(max_length=1)
