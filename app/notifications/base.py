from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LowStockAlert:
    item_id: int
    sku: str
    name: str
    quantity: int
    reorder_level: int

    def message(self) -> str:
        return (f"Low stock: {self.name} ({self.sku}) has {self.quantity} left "
                f"(reorder level {self.reorder_level})")


class Notifier(Protocol):
    """Anything with this method can be used as a notifier (duck typing,
    checked by type checkers). Implementations should not raise for delivery
    problems they can handle; callers also guard against it."""

    def low_stock(self, alert: LowStockAlert) -> None: ...
