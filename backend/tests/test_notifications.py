import uuid

from app.models.alert import SLATier
from app.services.notifications import (
    MockSMSNotification,
    MockVoiceNotification,
    NotificationService,
)


def test_mock_sms_notification_records_demo_delivery():
    sms = MockSMSNotification()
    service = NotificationService(sms=sms)
    alert_id = uuid.uuid4()

    record = service.notify_tier(alert_id, SLATier.Tier_1_Farm_Owner)

    assert record.notification_type == "sms"
    assert record.recipient == "demo-farm-owner"
    assert record.alert_id == alert_id
    assert "Veterinary verification required" in record.message
    assert sms.records == [record]


def test_mock_voice_notification_records_demo_delivery():
    voice = MockVoiceNotification()
    service = NotificationService(voice=voice)
    alert_id = uuid.uuid4()

    record = service.notify_tier(alert_id, SLATier.Tier_3_District_Officer)

    assert record.notification_type == "voice"
    assert record.recipient == "demo-district-officer"
    assert record.alert_id == alert_id
    assert voice.records == [record]