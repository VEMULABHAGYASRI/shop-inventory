from app.logging_config import get_logger
from app.notifications.base import LowStockAlert

logger = get_logger("notify")


class LogNotifier:
    """Default: just write alerts to the log. Needs no configuration."""

    def low_stock(self, alert: LowStockAlert) -> None:
        logger.warning(alert.message())
