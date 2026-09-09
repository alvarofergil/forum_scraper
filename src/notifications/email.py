"""Plain-text SMTP notification delivery."""

from __future__ import annotations

import json
import smtplib
from collections.abc import Sequence
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import EmailEnvironment, NotificationsConfig
from app.models import EventType, NotificationStatus, utc_now
from storage.orm import EventORM


class SMTPClient(Protocol):
    """Minimal SMTP client surface used by the email notifier."""

    def __enter__(self) -> SMTPClient:
        ...

    def __exit__(self, *args: object) -> None:
        ...

    def starttls(self) -> None:
        ...

    def login(self, user: str, password: str) -> None:
        ...

    def sendmail(self, sender: str, recipients: list[str], message: str) -> None:
        ...


class SMTPFactory(Protocol):
    """Factory for SMTP clients."""

    def __call__(self, host: str, port: int, *, timeout: float) -> SMTPClient:
        ...


@dataclass(frozen=True, slots=True)
class NotificationRetryResult:
    """Aggregate result for a notification delivery pass."""

    sent: int = 0
    failed: int = 0
    skipped: int = 0


class EmailNotificationService:
    """Deliver configured events through SMTP and record retryable status."""

    def __init__(
        self,
        *,
        session: Session,
        email_environment: EmailEnvironment,
        notifications: NotificationsConfig,
        smtp_factory: SMTPFactory = smtplib.SMTP,
        timeout_seconds: float = 20,
    ) -> None:
        self._session = session
        self._email_environment = email_environment
        self._notifications = notifications
        self._smtp_factory = smtp_factory
        self._timeout_seconds = timeout_seconds

    def send_pending(self) -> NotificationRetryResult:
        """Send pending notifications for configured event types."""

        return self._send_events_with_statuses((NotificationStatus.PENDING,))

    def retry_failed(self) -> NotificationRetryResult:
        """Retry notifications that failed in an earlier pass."""

        return self._send_events_with_statuses((NotificationStatus.FAILED,))

    def retry_pending_and_failed(self) -> NotificationRetryResult:
        """Retry all currently actionable notifications."""

        return self._send_events_with_statuses(
            (NotificationStatus.PENDING, NotificationStatus.FAILED)
        )

    def _send_events_with_statuses(
        self,
        statuses: Sequence[NotificationStatus],
    ) -> NotificationRetryResult:
        events = self._events_with_statuses(statuses)
        sent = 0
        failed = 0
        skipped = 0

        for event in events:
            if EventType(event.event_type) not in self._notifications.notify_event_types:
                skipped += 1
                continue

            try:
                self._send_event(event)
            except Exception as exc:
                event.notification_status = NotificationStatus.FAILED.value
                event.error_message = _safe_error_message(exc)
                failed += 1
            else:
                event.notification_status = NotificationStatus.SENT.value
                event.notified_at = utc_now()
                event.error_message = None
                sent += 1

        self._session.flush()
        return NotificationRetryResult(sent=sent, failed=failed, skipped=skipped)

    def _events_with_statuses(self, statuses: Sequence[NotificationStatus]) -> list[EventORM]:
        stmt = (
            select(EventORM)
            .where(EventORM.notification_status.in_([status.value for status in statuses]))
            .order_by(EventORM.created_at, EventORM.id)
        )
        return list(self._session.scalars(stmt))

    def _send_event(self, event: EventORM) -> None:
        message = EmailMessage()
        message["From"] = self._email_environment.smtp_user
        message["To"] = self._email_environment.notification_email
        message["Subject"] = f"[Forum Scraper] {event.event_type}"
        message.set_content(_event_body(event))

        with self._smtp_factory(
            self._email_environment.smtp_host,
            self._email_environment.smtp_port,
            timeout=self._timeout_seconds,
        ) as smtp:
            smtp.starttls()
            smtp.login(
                self._email_environment.smtp_user,
                self._email_environment.smtp_password,
            )
            smtp.sendmail(
                self._email_environment.smtp_user,
                [self._email_environment.notification_email],
                message.as_string(),
            )


def _event_body(event: EventORM) -> str:
    lines = [
        f"Event: {event.event_type}",
        f"Created at: {event.created_at.isoformat()}",
        f"Topic id: {event.topic_id or '-'}",
        f"Favorite id: {event.favorite_id or '-'}",
        f"Watch item id: {event.watch_item_id or '-'}",
    ]
    if event.payload_json is not None:
        lines.extend(
            [
                "",
                "Payload:",
                json.dumps(event.payload_json, ensure_ascii=True, indent=2, sort_keys=True),
            ]
        )
    return "\n".join(lines)


def _safe_error_message(exc: Exception) -> str:
    message = str(exc).strip()
    if not message:
        return exc.__class__.__name__
    return message[:1000]
