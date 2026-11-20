from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MovementReason(str, Enum):
    RECEIVED = "received"      # delivery from supplier   (+)
    SOLD = "sold"              # sold to a customer       (-)
    RETURNED = "returned"      # customer brought it back (+)
    DAMAGED = "damaged"        # broken / expired / lost  (-)
    ADJUSTMENT = "adjustment"  # stock-take correction    (+ or -)


POSITIVE_ONLY = {MovementReason.RECEIVED, MovementReason.RETURNED}
NEGATIVE_ONLY = {MovementReason.SOLD, MovementReason.DAMAGED}


class MovementCreate(BaseModel):
    change: Annotated[int, Field(ge=-1_000_000, le=1_000_000,
                                 description="Positive adds stock, negative removes it")]
    reason: MovementReason
    note: Annotated[str, Field(max_length=500)] | None = None

    @model_validator(mode="after")
    def sign_matches_reason(self):
        if self.change == 0:
            raise ValueError("change must not be 0")
        if self.reason in POSITIVE_ONLY and self.change < 0:
            raise ValueError(f"'{self.reason.value}' must have a positive change")
        if self.reason in NEGATIVE_ONLY and self.change > 0:
            raise ValueError(f"'{self.reason.value}' must have a negative change")
        return self


class _ItemBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sku: str
    name: str


class _UserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str


class MovementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    item: _ItemBrief
    user: _UserBrief
    change: int
    reason: MovementReason
    note: str | None
    quantity_after: int
    created_at: datetime
