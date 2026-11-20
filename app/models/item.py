from datetime import datetime

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._common import utcnow


class Item(Base):
    __tablename__ = "items"
    __table_args__ = (
        # Safety net: even if a bug skips the service check, the database
        # itself refuses negative stock or prices.
        CheckConstraint("quantity >= 0", name="ck_items_quantity_non_negative"),
        CheckConstraint("reorder_level >= 0", name="ck_items_reorder_non_negative"),
        CheckConstraint("unit_price_cents >= 0", name="ck_items_price_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    sku: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(100), default=None)
    # Changed only through StockMovement records (see services/stock_service.py).
    quantity: Mapped[int] = mapped_column(default=0)
    # When quantity falls to this level or below, the item counts as "low stock".
    reorder_level: Mapped[int] = mapped_column(default=0)
    # Integer cents: floats can't represent 0.10 exactly.
    unit_price_cents: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(default=utcnow, onupdate=utcnow)

    movements = relationship(
        "StockMovement",
        back_populates="item",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def is_low_stock(self) -> bool:
        """The business rule for "needs reordering", in exactly one place."""
        return self.quantity <= self.reorder_level
