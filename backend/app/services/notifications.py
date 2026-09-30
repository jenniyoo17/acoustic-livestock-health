import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from app.models.alert import SLATier

logger = logging.getLogger(__name__)
NotificationType = Literal["sms", "voice"]


@dataclass(frozen=True)
class NotificationRecord:
    recipient: str
    notification_type: NotificationType
    alert_id: uuid.UUID
    message: str
    timestamp: datetime


class MockSMSNotification:
    def __init__(self) -> None:
        self.records: list[NotificationRecord] = []

    def send(self, recipient: str, alert_id: uuid.UUID, message: str) -> NotificationRecord:
        record = NotificationRecord(
            recipient=recipient,
            notification_type="sms",
            alert_id=alert_id,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        self.records.append(record)
        logger.info("Demo SMS sent to %s for alert %s: %s", recipient, alert_id, message)
        return record


class MockVoiceNotification:
    def __init__(self) -> None:
        self.records: list[NotificationRecord] = []

    def send(self, recipient: str, alert_id: uuid.UUID, message: str) -> NotificationRecord:
        record = NotificationRecord(
            recipient=recipient,
            notification_type="voice",
            alert_id=alert_id,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        self.records.append(record)
        logger.info("Demo voice notification sent to %s for alert %s: %s", recipient, alert_id, message)
        return record


class NotificationService:
    """Dispatch demo notifications; no external SMS or voice provider is called."""

    def __init__(
        self,
        sms: MockSMSNotification | None = None,
        voice: MockVoiceNotification | None = None,
    ) -> None:
        self.sms = sms or MockSMSNotification()
        self.voice = voice or MockVoiceNotification()

    @property
    def records(self) -> list[NotificationRecord]:
        return [*self.sms.records, *self.voice.records]

    def notify_tier(self, alert_id: uuid.UUID, tier: SLATier) -> NotificationRecord:
        recipient_by_tier = {
            SLATier.Tier_1_Farm_Owner: "demo-farm-owner",
            SLATier.Tier_2_Field_Vet: "demo-field-vet",
            SLATier.Tier_3_District_Officer: "demo-district-officer",
        }
        message = f"Acoustic anomaly detected for alert {alert_id}. Veterinary verification required."
        recipient = recipient_by_tier[tier]
        if tier == SLATier.Tier_3_District_Officer:
            return self.voice.send(recipient, alert_id, message)
        return self.sms.send(recipient, alert_id, message)


notification_service = NotificationService()