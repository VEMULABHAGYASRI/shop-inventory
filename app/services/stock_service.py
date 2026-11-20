"""Stock changes. The ONLY place that modifies Item.quantity."""
from sqlalchemy import select, update
from sqlalchemy.orm import Session, joinedload

from app.errors import InsufficientStockError
from app.logging_config import get_logger
from app.models import Item, StockMovement
from app.models._common import utcnow
from app.notifications import LowStockAlert, Notifier
from app.services.item_service import get_item

logger = get_logger("stock")


def apply_movement(db: Session, item: Item, change: int, reason: str,
                   note: str | None, user_id: int) -> tuple[StockMovement, bool]:
    """Change stock inside the caller's transaction (does NOT commit).

    Returns the movement and whether the item just became low on stock.
    """
    # One atomic UPDATE: the database checks and changes the quantity in a
    # single step, so two simultaneous sales of the last item can't both win.
    new_quantity = db.execute(
        update(Item)
        .where(Item.id == item.id, Item.quantity + change >= 0)
        .values(quantity=Item.quantity + change, updated_at=utcnow())
        .returning(Item.quantity)
    ).scalar_one_or_none()

    if new_quantity is None:
        db.rollback()
        raise InsufficientStockError(
            f"Cannot remove {-change} of {item.sku}: only {item.quantity} in stock"
        )

    db.refresh(item)
    movement = StockMovement(item_id=item.id, change=change, reason=reason, note=note,
                             quantity_after=new_quantity, user_id=user_id)
    db.add(movement)

    old_quantity = new_quantity - change
    became_low = old_quantity > item.reorder_level >= new_quantity
    return movement, became_low


def record_movement(db: Session, notifier: Notifier, *, item_id: int, change: int,
                    reason: str, note: str | None, user_id: int) -> StockMovement:
    item = get_item(db, item_id)
    movement, became_low = apply_movement(db, item, change, reason, note, user_id)
    db.commit()  # commit BEFORE notifying: only alert about changes that stuck
    logger.info("Stock %s %+d (%s) -> %d by user %s",
                item.sku, change, reason, movement.quantity_after, user_id)

    if became_low:
        alert = LowStockAlert(item.id, item.sku, item.name, item.quantity, item.reorder_level)
        try:
            notifier.low_stock(alert)
        except Exception:
            logger.exception("Notifier failed for %s", item.sku)
    return _load(db, movement.id)


def _load(db: Session, movement_id: int) -> StockMovement:
    return db.scalars(_with_relations(select(StockMovement))
                      .where(StockMovement.id == movement_id)).one()


def _with_relations(query):
    # Load item and user in the same query (avoids one extra query per row).
    return query.options(joinedload(StockMovement.item), joinedload(StockMovement.user))


def list_movements(db: Session, item_id: int | None = None, limit: int = 50) -> list[StockMovement]:
    """Newest first. With item_id: one item's history; without: shop-wide feed."""
    query = _with_relations(select(StockMovement)).order_by(StockMovement.id.desc()).limit(limit)
    if item_id is not None:
        get_item(db, item_id)  # 404 for unknown items rather than an empty list
        query = query.where(StockMovement.item_id == item_id)
    return list(db.scalars(query))
