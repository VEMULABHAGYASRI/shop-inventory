from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.logging_config import get_logger
from app.models import Item

logger = get_logger("items")


def _normalize_sku(sku: str) -> str:
    return sku.strip().upper()


def _clean_category(category: str | None) -> str | None:
    if category is None:
        return None
    return category.strip() or None


def _ensure_sku_free(db: Session, sku: str, exclude_id: int | None = None) -> None:
    query = select(Item.id).where(Item.sku == sku)
    if exclude_id is not None:
        query = query.where(Item.id != exclude_id)
    if db.scalar(query) is not None:
        raise ConflictError(f"An item with SKU '{sku}' already exists")


def list_items(
    db: Session,
    search: str | None = None,
    category: str | None = None,
    low_stock_only: bool = False,
) -> list[Item]:
    query = select(Item).order_by(Item.name)
    if search:
        # autoescape: a search for "50%" means the text "50%", not a wildcard.
        query = query.where(or_(
            Item.name.icontains(search, autoescape=True),
            Item.sku.icontains(search, autoescape=True),
        ))
    if category:
        query = query.where(Item.category == category)
    if low_stock_only:
        query = query.where(Item.quantity <= Item.reorder_level)
    return list(db.scalars(query))


def list_categories(db: Session) -> list[str]:
    query = select(Item.category).where(Item.category.is_not(None)).distinct().order_by(Item.category)
    return list(db.scalars(query))


def get_item(db: Session, item_id: int) -> Item:
    item = db.get(Item, item_id)
    if item is None:
        raise NotFoundError(f"Item {item_id} not found")
    return item


def create_item(db: Session, *, user_id: int, sku: str, name: str,
                category: str | None = None, reorder_level: int = 0,
                unit_price_cents: int = 0, initial_quantity: int = 0) -> Item:
    from app.services.stock_service import apply_movement  # avoid circular import

    sku = _normalize_sku(sku)
    _ensure_sku_free(db, sku)
    item = Item(
        sku=sku, name=name.strip(), category=_clean_category(category),
        reorder_level=reorder_level, unit_price_cents=unit_price_cents,
    )
    db.add(item)
    db.flush()  # assigns item.id without committing yet
    if initial_quantity:
        # Opening stock is recorded as a movement too, so history adds up.
        apply_movement(db, item, initial_quantity, "received", "Initial stock", user_id)
    db.commit()  # item + opening movement saved together, or not at all
    logger.info("Created item %s (id=%s)", item.sku, item.id)
    return item


def update_item(db: Session, item_id: int, changes: dict) -> Item:
    """`changes` holds only the fields the client actually sent."""
    item = get_item(db, item_id)
    if changes.get("sku") is not None:
        changes["sku"] = _normalize_sku(changes["sku"])
        _ensure_sku_free(db, changes["sku"], exclude_id=item.id)
    if "category" in changes:
        changes["category"] = _clean_category(changes["category"])
    if changes.get("name") is not None:
        changes["name"] = changes["name"].strip()
    for field, value in changes.items():
        if value is None and field != "category":
            continue  # only category may be cleared
        setattr(item, field, value)
    db.commit()
    logger.info("Updated item %s: %s", item.id, sorted(changes))
    return item


def delete_item(db: Session, item_id: int) -> None:
    """Deletes the item *and its movement history*."""
    item = get_item(db, item_id)
    db.delete(item)
    db.commit()
    logger.info("Deleted item %s (id=%s)", item.sku, item_id)
