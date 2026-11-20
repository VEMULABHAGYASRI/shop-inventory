from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

# Reusable validated types: one definition of each rule, used by both
# ItemCreate and ItemUpdate so they can never drift apart.
Sku = Annotated[str, Field(min_length=1, max_length=40, pattern=r"^[A-Za-z0-9_.\- ]+$",
                           description="Your product code, e.g. RICE-5KG")]
Name = Annotated[str, Field(min_length=1, max_length=200)]
Category = Annotated[str, Field(max_length=100)]
ReorderLevel = Annotated[int, Field(ge=0, le=1_000_000,
                                    description="Low-stock when quantity is at or below this")]
PriceCents = Annotated[int, Field(ge=0, le=100_000_000,
                                  description="Price in cents (e.g. 250 = 2.50)")]


class ItemCreate(BaseModel):
    sku: Sku
    name: Name
    category: Category | None = None
    reorder_level: ReorderLevel = 0
    unit_price_cents: PriceCents = 0


class ItemUpdate(BaseModel):
    """Every field optional: PATCH sends only what changes.

    There is deliberately no `quantity` here: stock changes go through
    POST /api/items/{id}/movements so they are always recorded.
    """

    sku: Sku | None = None
    name: Name | None = None
    category: Category | None = None
    reorder_level: ReorderLevel | None = None
    unit_price_cents: PriceCents | None = None


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: str | None
    quantity: int
    reorder_level: int
    unit_price_cents: int
    is_low_stock: bool
    created_at: datetime
    updated_at: datetime
