"""Outgoing notifications (the app's only external integration).

Services depend on the `Notifier` interface, never on a concrete class, so
the real webhook sender can be swapped for a fake in tests, or for a new
implementation (email, SMS, ...) without touching business logic.
"""
from app.notifications.base import LowStockAlert, Notifier
from app.notifications.factory import build_notifier

__all__ = ["LowStockAlert", "Notifier", "build_notifier"]
