from app.config import Settings
from app.notifications.base import Notifier
from app.notifications.log_notifier import LogNotifier
from app.notifications.webhook_notifier import WebhookNotifier


def build_notifier(settings: Settings) -> Notifier:
    """Pick the real notifier from configuration."""
    if settings.low_stock_webhook_url:
        return WebhookNotifier(settings.low_stock_webhook_url)
    return LogNotifier()
