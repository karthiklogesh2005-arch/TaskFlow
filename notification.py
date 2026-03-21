"""Notification helpers for TaskFlow using the plyer library."""

from __future__ import annotations

from plyer import notification as plyer_notification


def send_notification(title: str, message: str, timeout: int = 10) -> None:
    """Send a desktop notification using plyer."""
    plyer_notification.notify(
        title=title,
        message=message,
        app_name="TaskFlow",
        timeout=timeout,
    )
