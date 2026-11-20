"""Test stand-ins for external integrations."""
from app.notifications import LowStockAlert


class FakeNotifier:
    """Records alerts instead of sending them."""

    def __init__(self):
        self.alerts: list[LowStockAlert] = []

    def low_stock(self, alert: LowStockAlert) -> None:
        self.alerts.append(alert)


class BrokenNotifier:
    """Simulates an integration that crashes."""

    def low_stock(self, alert: LowStockAlert) -> None:
        raise RuntimeError("notification service is down")
