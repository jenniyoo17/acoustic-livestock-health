import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertStatus, SLATier
from app.schemas.acoustic_event import AcousticEventResponse
from app.schemas.alert import AlertResponse
from app.schemas.device import DeviceResponse
from app.schemas.shed import ShedResponse


class EscalationRecordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    from_tier: SLATier | None
    to_tier: SLATier
    reason: str
    triggered_at: datetime
    acknowledged_at: datetime | None
    created_at: datetime


class AcknowledgeRequest(BaseModel):
    tier: SLATier


class AcknowledgeResponse(BaseModel):
    alert_id: uuid.UUID
    status: AlertStatus
    acknowledged_tier: SLATier
    current_sla_tier: SLATier
    acknowledged_at: datetime


class AlertSLAStatus(BaseModel):
    alert_id: uuid.UUID
    status: AlertStatus
    current_sla_tier: SLATier
    triggered_at: datetime
    deadline: datetime | None
    remaining_seconds: float | None
    sla_enabled: bool
    sla_breached: bool
    acknowledged_at: datetime | None
    escalation_history: list[EscalationRecordResponse]


class EscalationEvaluationResponse(BaseModel):
    evaluated_at: datetime
    escalated_count: int
    statuses: list[AlertSLAStatus]


class AlertDetailResponse(BaseModel):
    alert: AlertResponse
    acoustic_event: AcousticEventResponse
    shed: ShedResponse
    device: DeviceResponse
    sla: AlertSLAStatus