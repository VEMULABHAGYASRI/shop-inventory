from datetime import datetime

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models._common import utcnow


class StockMovement(Base):
    """One change to an item's stock: the audit trail of the shop."""

    __tablename__ = "stock_movements"
    __table_args__ = (CheckConstraint("change != 0", name="ck_movements_nonzero"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id", ondelete="CASCADE"), index=True
    )
    change: Mapped[int]  # +12 received, -1 sold, ...
    reason: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(500), default=None)
    quantity_after: Mapped[int]
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    item = relationship("Item", back_populates="movements")
    user = relationship("User")
