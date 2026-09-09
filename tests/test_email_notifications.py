from __future__ import annotations

from pathlib import Path

from alembic.config import Config

from alembic import command
from app.config import EmailEnvironment, NotificationsConfig
from app.models import EventType, NotificationStatus
from events.service import EventService
from notifications.email import EmailNotificationService
from storage import create_sqlite_engine, session_factory, session_scope
from storage.orm import EventORM, TopicORM


def migrated_db_path(tmp_path: Path) -> Path:
    db_path = tmp_path / "monitor.db"
    config = Config("alembic.ini")
    config.set_main_option("script_location", "alembic")
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    command.upgrade(config, "head")
    return db_path


def create_topic(session) -> TopicORM:  # type: ignore[no-untyped-def]
    topic = TopicORM(
        external_topic_id="123",
        canonical_url="https://www.armas.es/foros/viewtopic.php?f=96&t=123",
        title="Topic",
    )
    session.add(topic)
    session.flush()
    return topic


def email_environment() -> EmailEnvironment:
    return EmailEnvironment(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="sender@example.test",
        smtp_password="env-secret",
        notification_email="recipient@example.test",
    )


class FakeSMTP:
    sent_messages: list[dict[str, object]] = []
    fail_send: bool = False

    def __init__(self, host: str, port: int, timeout: float) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout

    def __enter__(self) -> FakeSMTP:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def starttls(self) -> None:
        return None

    def login(self, user: str, password: str) -> None:
        self.user = user
        self.password = password

    def sendmail(self, sender: str, recipients: list[str], message: str) -> None:
        if self.fail_send:
            raise OSError("smtp unavailable")
        self.sent_messages.append(
            {
                "host": self.host,
                "port": self.port,
                "sender": sender,
                "recipients": recipients,
                "message": message,
            }
        )


def test_smtp_fake_sends_configured_event_and_marks_sent(tmp_path: Path) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = False
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        event, _created = EventService(session).emit_for_topic(
            event_type=EventType.NEW_FAVORITE,
            topic_external_id=topic.external_topic_id,
            content_hash="abc",
            topic_id=topic.id,
            payload={"title": "Topic", "url": topic.canonical_url},
        )

        result = EmailNotificationService(
            session=session,
            email_environment=email_environment(),
            notifications=NotificationsConfig(notify_event_types=(EventType.NEW_FAVORITE,)),
            smtp_factory=FakeSMTP,
        ).send_pending()

        assert result.sent == 1
        assert result.failed == 0
        assert event.notification_status == NotificationStatus.SENT.value
        assert event.notified_at is not None
        assert event.error_message is None
        assert len(FakeSMTP.sent_messages) == 1
        message = str(FakeSMTP.sent_messages[0]["message"])
        assert "Subject: [Forum Scraper] NEW_FAVORITE" in message
        assert "Topic" in message
        assert "env-secret" not in message


def test_event_type_not_configured_is_not_sent(tmp_path: Path) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = False
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        event, _created = EventService(session).emit_for_topic(
            event_type=EventType.ERROR,
            topic_external_id=topic.external_topic_id,
            content_hash="err",
            topic_id=topic.id,
            payload={"message": "temporary failure"},
        )

        result = EmailNotificationService(
            session=session,
            email_environment=email_environment(),
            notifications=NotificationsConfig(notify_event_types=(EventType.NEW_FAVORITE,)),
            smtp_factory=FakeSMTP,
        ).send_pending()

        assert result.sent == 0
        assert result.skipped == 1
        assert event.notification_status == NotificationStatus.PENDING.value
        assert FakeSMTP.sent_messages == []


def test_smtp_failure_marks_event_failed_and_retry_sends_it(tmp_path: Path) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = True
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        event, _created = EventService(session).emit_for_topic(
            event_type=EventType.PRICE_CHANGED,
            topic_external_id=topic.external_topic_id,
            content_hash="price-1",
            topic_id=topic.id,
            payload={"old_price": "100.00", "new_price": "90.00"},
        )

        first = EmailNotificationService(
            session=session,
            email_environment=email_environment(),
            notifications=NotificationsConfig(notify_event_types=(EventType.PRICE_CHANGED,)),
            smtp_factory=FakeSMTP,
        ).send_pending()

        assert first.failed == 1
        assert event.notification_status == NotificationStatus.FAILED.value
        assert event.notified_at is None
        assert event.error_message == "smtp unavailable"

        FakeSMTP.fail_send = False
        retry = EmailNotificationService(
            session=session,
            email_environment=email_environment(),
            notifications=NotificationsConfig(notify_event_types=(EventType.PRICE_CHANGED,)),
            smtp_factory=FakeSMTP,
        ).retry_failed()

        assert retry.sent == 1
        assert event.notification_status == NotificationStatus.SENT.value
        assert event.notified_at is not None
        assert event.error_message is None


def test_retry_pending_and_failed_processes_both_statuses(tmp_path: Path) -> None:
    FakeSMTP.sent_messages = []
    FakeSMTP.fail_send = False
    engine = create_sqlite_engine(migrated_db_path(tmp_path))
    factory = session_factory(engine)

    with session_scope(factory) as session:
        topic = create_topic(session)
        pending, _created = EventService(session).emit_for_topic(
            event_type=EventType.NEW_FAVORITE,
            topic_external_id=topic.external_topic_id,
            content_hash="pending",
            topic_id=topic.id,
        )
        failed, _created = EventService(session).emit_for_topic(
            event_type=EventType.NEW_FAVORITE,
            topic_external_id=topic.external_topic_id,
            content_hash="failed",
            topic_id=topic.id,
        )
        failed.notification_status = NotificationStatus.FAILED.value

        result = EmailNotificationService(
            session=session,
            email_environment=email_environment(),
            notifications=NotificationsConfig(notify_event_types=(EventType.NEW_FAVORITE,)),
            smtp_factory=FakeSMTP,
        ).retry_pending_and_failed()

        assert result.sent == 2
        assert {pending.notification_status, failed.notification_status} == {
            NotificationStatus.SENT.value
        }
        assert session.query(EventORM).count() == 2
