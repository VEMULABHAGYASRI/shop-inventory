import httpx

from app.logging_config import get_logger
from app.notifications.base import LowStockAlert

logger = get_logger("notify")


class WebhookNotifier:
    """POSTs the alert text to a URL, e.g. an ntfy.sh topic, which pushes it
    to your phone.

    The httpx client is injectable so tests can pass one with a mock
    transport and never touch the network.
    """

    def __init__(self, url: str, client: httpx.Client | None = None, timeout: float = 5.0):
        self.url = url
        self.client = client or httpx.Client(timeout=timeout)

    def low_stock(self, alert: LowStockAlert) -> None:
        try:
            resp = self.client.post(
                self.url,
                content=alert.message().encode(),
                headers={"Title": "Shop inventory", "Tags": "warning"},
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            # The stock change already succeeded; a failed alert must not
            # turn it into an error. Log loudly and move on.
            logger.error("Low-stock webhook failed for %s: %s", alert.sku, exc)
