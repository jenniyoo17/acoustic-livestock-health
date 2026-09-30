import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.alert import AlertStatus, AnomalySeverity, SLATier


class AlertFields(BaseModel):
    acoustic_event_id: uuid.UUID
    shed_id: uuid.UUID
    anomaly_severity: AnomalySeverity
    status: AlertStatus = AlertStatus.Pending_Triage
    current_sla_tier: SLATier = SLATier.Tier_1_Farm_Owner


class AlertCreate(AlertFields):
    pass


class AlertResponse(AlertFields):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    triggered_at: datetime
    resolved_at: datetime | None = None
