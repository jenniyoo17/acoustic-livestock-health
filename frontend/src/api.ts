export type AlertStatus =
  | 'Pending_Triage'
  | 'Escalated'
  | 'Under_Vet_Review'
  | 'Verified_Risk'
  | 'False_Positive'
  | 'Resolved';

export type AnomalySeverity = 'Low' | 'Medium' | 'High' | 'Critical';

export type SLATier =
  | 'Tier_1_Farm_Owner'
  | 'Tier_2_Field_Vet'
  | 'Tier_3_District_Officer';

export type DeviceStatus = 'Online' | 'Offline' | 'Degraded';
export type VetOutcome = 'Verified_Risk' | 'False_Positive';
export type LabReferralStatus =
  | 'Pending'
  | 'Sample_Collected'
  | 'In_Lab'
  | 'Result_Available'
  | 'Cancelled';

export interface AlertSLAStatus {
  alert_id: string;
  status: AlertStatus;
  current_sla_tier: SLATier;
  triggered_at: string;
  deadline: string | null;
  remaining_seconds: number | null;
  sla_enabled: boolean;
  sla_breached: boolean;
  acknowledged_at: string | null;
  escalation_history: EscalationRecord[];
}

export interface EscalationRecord {
  id: string;
  alert_id: string;
  from_tier: SLATier | null;
  to_tier: SLATier;
  reason: string;
  triggered_at: string;
  acknowledged_at: string | null;
  created_at: string;
}

export interface AcousticEventResponse {
  id: string;
  device_id: string;
  shed_id: string;
  event_type: string;
  confidence_score: number;
  yamnet_embedding_vector: number[];
  audio_duration_sec: number;
  audio_snippet_url: string | null;
  recorded_at: string;
  is_synced_offline: boolean;
  created_at: string;
}

export interface AlertResponse {
  id: string;
  acoustic_event_id: string;
  shed_id: string;
  anomaly_severity: AnomalySeverity;
  status: AlertStatus;
  current_sla_tier: SLATier;
  triggered_at: string;
  resolved_at: string | null;
}

export interface ShedResponse {
  id: string;
  farm_id: string;
  shed_number: string;
  animal_type: string;
  capacity: number;
  current_count: number;
  created_at: string;
}

export interface DeviceResponse {
  id: string;
  shed_id: string;
  device_uid: string;
  firmware_version: string;
  status: DeviceStatus;
  public_key: string | null;
  last_heartbeat_at: string | null;
  created_at: string;
}

export interface AlertDetailResponse {
  alert: AlertResponse;
  acoustic_event: AcousticEventResponse;
  shed: ShedResponse;
  device: DeviceResponse;
  sla: AlertSLAStatus;
}

export interface VetVerificationResponse {
  verification_id: string;
  alert_id: string;
  verification_result: VetOutcome;
  alert_status: AlertStatus;
  vet_identifier: string;
  verified_at: string;
}

export interface VetVerificationDetail {
  id: string;
  alert_id: string;
  vet_identifier: string;
  verification_status: VetOutcome;
  assessment_notes: string;
  verified_at: string;
  created_at: string;
}

export interface LabReferralResponse {
  id: string;
  alert_id: string;
  verification_id: string;
  sample_identifier: string;
  requested_tests: string[];
  status: LabReferralStatus;
  referred_at: string;
  result: string | null;
  result_at: string | null;
  notes: string;
  is_demo_result: boolean;
  created_at: string;
}

export interface LabReferralDetail {
  referral: LabReferralResponse;
  alert: AlertResponse;
  verification: VetVerificationDetail;
}

export interface AuditBlockResponse {
  block_index: number;
  timestamp: string;
  previous_hash: string | null;
  entity_type: string;
  entity_id: string;
  payload_hash: string;
  block_hash: string;
}

export interface AuditIntegrityResponse {
  valid: boolean;
  checked_blocks: number;
  error: string | null;
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers ?? {}),
    },
    ...options,
  });

  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    const message = typeof detail === 'object' && detail && 'detail' in detail ? String(detail.detail) : 'Request failed';
    throw new Error(message);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}

export const api = {
  getHealth: () => request<{ status: string }>(`/api/v1/health`),
  getEscalationStatus: () => request<AlertSLAStatus[]>(`/api/v1/alerts/escalation-status`),
  getAlertDetail: (alertId: string) => request<AlertDetailResponse>(`/api/v1/alerts/${alertId}`),
  acknowledgeAlert: (alertId: string, tier: SLATier) =>
    request<{ alert_id: string; status: AlertStatus; acknowledged_tier: SLATier; current_sla_tier: SLATier; acknowledged_at: string }>(
      `/api/v1/alerts/${alertId}/acknowledge`,
      {
        method: 'POST',
        body: JSON.stringify({ tier }),
      },
    ),
  submitVetVerification: (payload: {
    alert_id: string;
    outcome: VetOutcome;
    vet_identifier: string;
    notes: string;
  }) =>
    request<VetVerificationResponse>(`/api/v1/vet/verify`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  createLabReferral: (payload: {
    alert_id: string;
    sample_identifier: string;
    requested_tests: string[];
    notes?: string;
  }) =>
    request<LabReferralResponse>(`/api/v1/lab/referrals`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getLabReferral: (referralId: string) => request<LabReferralDetail>(`/api/v1/lab/referrals/${referralId}`),
  updateLabReferralStatus: (referralId: string, status: LabReferralStatus, result?: string, notes?: string) =>
    request<LabReferralResponse>(`/api/v1/lab/referrals/${referralId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, result, notes }),
    }),
  getAuditChain: () => request<AuditBlockResponse[]>(`/api/v1/audit/chain`),
  verifyAuditIntegrity: () => request<AuditIntegrityResponse>(`/api/v1/audit/verify-integrity`, { method: 'POST' }),
  getGeoClusters: () => request<{ clusters: unknown[] }>(`/api/v1/geo/outbreak-clusters`),
  getGovernmentExport: () => request<unknown>(`/api/v1/export/government-nadrs`),
};

export const backendUnavailableMessage =
  'This endpoint is not exposed by the current backend. The frontend is showing the real available state only.';
