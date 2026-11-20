"""The webhook notifier, tested with a fake HTTP transport: no network."""
import httpx

from app.config import Settings
from app.notifications import LowStockAlert, build_notifier
from app.notifications.log_notifier import LogNotifier
from app.notifications.webhook_notifier import WebhookNotifier

ALERT = LowStockAlert(item_id=1, sku="MILK", name="Milk 1L", quantity=2, reorder_level=5)


def test_webhook_posts_alert_message():
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    WebhookNotifier("https://example.test/hook", client=client).low_stock(ALERT)

    assert len(requests) == 1
    assert str(requests[0].url) == "https://example.test/hook"
    assert b"Milk 1L (MILK) has 2 left" in requests[0].content


def test_webhook_failure_is_logged_not_raised(caplog):
    def handler(request):
        raise httpx.ConnectError("no route to host")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    WebhookNotifier("https://example.test/hook", client=client).low_stock(ALERT)
    assert "Low-stock webhook failed" in caplog.text


def test_webhook_http_error_status_is_logged(caplog):
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(500)))
    WebhookNotifier("https://example.test/hook", client=client).low_stock(ALERT)
    assert "Low-stock webhook failed" in caplog.text


def _settings(**kw):
    return Settings(_env_file=None, secret_key="test-secret-key-that-is-long-enough", **kw)


def test_factory_defaults_to_log_notifier():
    assert isinstance(build_notifier(_settings()), LogNotifier)


def test_factory_uses_webhook_when_configured():
    notifier = build_notifier(_settings(low_stock_webhook_url="https://example.test/hook"))
    assert isinstance(notifier, WebhookNotifier)
