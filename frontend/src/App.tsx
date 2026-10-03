import { useEffect, useMemo, useState } from 'react';
import {
  api,
  backendUnavailableMessage,
  type AlertDetailResponse,
  type AlertSLAStatus,
  type AuditBlockResponse,
  type LabReferralResponse,
  type SLATier,
  type VetOutcome,
} from './api';

type PageKey =
  | 'command-center'
  | 'alerts-sla'
  | 'vet-lab'
  | 'edge-monitor'
  | 'audit-ledger'
  | 'government-export';

const navItems: Array<{ key: PageKey; label: string }> = [
  { key: 'command-center', label: 'Command Center' },
  { key: 'alerts-sla', label: 'Alerts & SLA' },
  { key: 'vet-lab', label: 'Vet / Lab Workbench' },
  { key: 'edge-monitor', label: 'Edge Monitor' },
  { key: 'audit-ledger', label: 'Audit Ledger' },
  { key: 'government-export', label: 'Government Export' },
];

const medicalDisclaimer =
  'Acoustic Early-Warning & Anomaly Detection only.\nAlerts require registered veterinarian clinical verification.\nThis system does not diagnose or prescribe treatment.';

function formatDate(value: string | null | undefined) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}

function StatusBadge({ value }: { value: string }) {
  return <span className={`status-badge status-${String(value).toLowerCase()}`}>{value}</span>;
}

function SectionCard({ title, children, actions }: { title: string; children: React.ReactNode; actions?: React.ReactNode }) {
  return (
    <section className="data-card">
      <div className="card-header">
        <h3>{title}</h3>
        {actions}
      </div>
      {children}
    </section>
  );
}

function BackendState({ error, actionLabel, onRetry }: { error: string; actionLabel?: string; onRetry?: () => void }) {
  return (
    <div className="empty-state compact" role="alert">
      <h3>Backend unavailable</h3>
      <p>{error}</p>
      {onRetry && (
        <button type="button" className="primary-button" onClick={onRetry}>
          {actionLabel ?? 'Retry'}
        </button>
      )}
    </div>
  );
}

function CommandCenterPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<AlertSLAStatus[]>([]);
  const [details, setDetails] = useState<Record<string, AlertDetailResponse>>({});

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getEscalationStatus();
      setStatuses(response);
      const detailEntries = await Promise.all(
        response.map(async (status) => {
          try {
            const detail = await api.getAlertDetail(status.alert_id);
            return [status.alert_id, detail] as const;
          } catch {
            return null;
          }
        }),
      );
      const nextDetails = Object.fromEntries(
        detailEntries.filter((entry): entry is readonly [string, AlertDetailResponse] => Boolean(entry)),
      );
      setDetails(nextDetails);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load command center data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const summaries = useMemo(() => {
    const active = statuses.filter((item) => item.status !== 'Resolved' && item.status !== 'False_Positive' && item.status !== 'Verified_Risk');
    const critical = statuses.filter((item) => {
      const detail = details[item.alert_id];
      return detail ? detail.alert.anomaly_severity === 'High' || detail.alert.anomaly_severity === 'Critical' : false;
    });
    const awaitingVet = statuses.filter((item) => {
      const detail = details[item.alert_id];
      return detail ? detail.alert.status === 'Under_Vet_Review' : item.status === 'Under_Vet_Review';
    });
    const deviceStatus = Object.values(details).reduce(
      (acc, detail) => {
        acc[detail.device.status] = (acc[detail.device.status] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );
    const severityCounts = Object.values(details).reduce(
      (acc, detail) => {
        const key = detail.alert.anomaly_severity;
        acc[key] = (acc[key] ?? 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    );

    return {
      totalAlerts: statuses.length,
      activeAlerts: active.length,
      highCritical: critical.length,
      awaitingVet: awaitingVet.length,
      deviceStatus,
      severityCounts,
      recent: [...statuses].sort((a, b) => new Date(b.triggered_at).getTime() - new Date(a.triggered_at).getTime()).slice(0, 5),
    };
  }, [statuses, details]);

  if (loading) {
    return <div className="panel-loading">Loading command center…</div>;
  }

  if (error) {
    return <BackendState error={error} onRetry={load} />;
  }

  return (
    <div className="stack gap-lg">
      <div className="summary-grid">
        <div className="summary-tile"><span>Total alerts</span><strong>{summaries.totalAlerts}</strong></div>
        <div className="summary-tile"><span>Active alerts</span><strong>{summaries.activeAlerts}</strong></div>
        <div className="summary-tile"><span>High / Critical</span><strong>{summaries.highCritical}</strong></div>
        <div className="summary-tile"><span>Awaiting vet</span><strong>{summaries.awaitingVet}</strong></div>
      </div>

      <div className="row-two-col">
        <SectionCard title="Severity distribution">
          <div className="metric-list">
            {Object.entries(summaries.severityCounts).length ? (
              Object.entries(summaries.severityCounts).map(([label, count]) => (
                <div className="metric-row" key={label}>
                  <span>{label}</span>
                  <strong>{count}</strong>
                </div>
              ))
            ) : (
              <p className="muted">No severity data is available from the current backend.</p>
            )}
          </div>
        </SectionCard>

        <SectionCard title="Device health">
          <div className="metric-list">
            {Object.entries(summaries.deviceStatus).length ? (
              Object.entries(summaries.deviceStatus).map(([label, count]) => (
                <div className="metric-row" key={label}>
                  <span>{label}</span>
                  <strong>{count}</strong>
                </div>
              ))
            ) : (
              <p className="muted">No device telemetry is currently exposed by the backend.</p>
            )}
          </div>
        </SectionCard>
      </div>

      <SectionCard title="Recent alerts">
        <div className="table-list compact-table">
          {summaries.recent.length ? (
            summaries.recent.map((item) => {
              const detail = details[item.alert_id];
              return (
                <div className="table-row" key={item.alert_id}>
                  <span>{detail ? detail.device.device_uid : 'Alert'}</span>
                  <span>{detail ? detail.alert.anomaly_severity : item.status}</span>
                  <span>{item.current_sla_tier}</span>
                  <span>{formatDate(item.triggered_at)}</span>
                </div>
              );
            })
          ) : (
            <p className="muted">No recent alert activity is available.</p>
          )}
        </div>
      </SectionCard>

      <SectionCard title="Acoustic Risk Clusters">
        <div className="empty-state compact">
          <h3>Geographic cluster endpoint unavailable</h3>
          <p>{backendUnavailableMessage}</p>
        </div>
      </SectionCard>
    </div>
  );
}

function AlertsSlaPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statuses, setStatuses] = useState<AlertSLAStatus[]>([]);
  const [details, setDetails] = useState<Record<string, AlertDetailResponse>>({});
  const [severityFilter, setSeverityFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('all');
  const [tierFilter, setTierFilter] = useState('all');
  const [eventFilter, setEventFilter] = useState('all');

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getEscalationStatus();
      setStatuses(response);
      const nextDetails = Object.fromEntries(
        (
          await Promise.all(
            response.map(async (status) => {
              try {
                const detail = await api.getAlertDetail(status.alert_id);
                return [status.alert_id, detail] as const;
              } catch {
                return null;
              }
            }),
          )
        ).filter((entry): entry is readonly [string, AlertDetailResponse] => Boolean(entry)),
      );
      setDetails(nextDetails);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load alert operations board.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const filtered = useMemo(() => {
    return statuses.filter((status) => {
      const detail = details[status.alert_id];
      const severity = detail?.alert.anomaly_severity ?? 'Unknown';
      const eventType = detail?.acoustic_event.event_type ?? 'Unknown';
      return (
        (severityFilter === 'all' || severity === severityFilter) &&
        (statusFilter === 'all' || status.status === statusFilter) &&
        (tierFilter === 'all' || status.current_sla_tier === tierFilter) &&
        (eventFilter === 'all' || eventType === eventFilter)
      );
    });
  }, [statuses, details, severityFilter, statusFilter, tierFilter, eventFilter]);

  const ackAlert = async (alertId: string, tier: SLATier) => {
    try {
      await api.acknowledgeAlert(alertId, tier);
      await load();
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Acknowledgement failed.');
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading alert board…</div>;
  }

  if (error) {
    return <BackendState error={error} onRetry={load} />;
  }

  return (
    <div className="stack gap-lg">
      <div className="filter-row">
        <label>
          Severity
          <select value={severityFilter} onChange={(event) => setSeverityFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="Low">Low</option>
            <option value="Medium">Medium</option>
            <option value="High">High</option>
            <option value="Critical">Critical</option>
          </select>
        </label>
        <label>
          Status
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="Pending_Triage">Pending_Triage</option>
            <option value="Escalated">Escalated</option>
            <option value="Under_Vet_Review">Under_Vet_Review</option>
            <option value="Verified_Risk">Verified_Risk</option>
            <option value="False_Positive">False_Positive</option>
            <option value="Resolved">Resolved</option>
          </select>
        </label>
        <label>
          SLA tier
          <select value={tierFilter} onChange={(event) => setTierFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="Tier_1_Farm_Owner">Tier 1</option>
            <option value="Tier_2_Field_Vet">Tier 2</option>
            <option value="Tier_3_District_Officer">Tier 3</option>
          </select>
        </label>
        <label>
          Event type
          <select value={eventFilter} onChange={(event) => setEventFilter(event.target.value)}>
            <option value="all">All</option>
            <option value="Cough">Cough</option>
            <option value="Distress_Call">Distress_Call</option>
            <option value="Rumination_Change">Rumination_Change</option>
            <option value="Environmental_Noise">Environmental_Noise</option>
          </select>
        </label>
      </div>

      <SectionCard title="Operations board">
        <div className="table-list">
          {filtered.map((status) => {
            const detail = details[status.alert_id];
            const severity = detail?.alert.anomaly_severity ?? 'Low';
            const currentTier = status.current_sla_tier;

            return (
              <div className="alert-row" key={status.alert_id}>
                <div>
                  <div className="row-title">{detail?.device.device_uid ?? 'Device unavailable'}</div>
                  <div className="muted">{detail?.shed.shed_number ?? 'Shed unavailable'} • {detail?.acoustic_event.event_type ?? 'Event unavailable'}</div>
                </div>
                <div>
                  <div className="row-title">Confidence</div>
                  <div className="muted">{detail ? `${(detail.acoustic_event.confidence_score * 100).toFixed(0)}%` : '—'}</div>
                </div>
                <div>
                  <div className="row-title">Severity</div>
                  <StatusBadge value={severity} />
                </div>
                <div>
                  <div className="row-title">Status</div>
                  <StatusBadge value={status.status} />
                </div>
                <div>
                  <div className="row-title">SLA</div>
                  <div className="muted">{currentTier}</div>
                </div>
                <div>
                  <div className="row-title">Triggered</div>
                  <div className="muted">{formatDate(status.triggered_at)}</div>
                </div>
                <div className="action-group">
                  <button
                    type="button"
                    className="secondary-button"
                    onClick={() => ackAlert(status.alert_id, currentTier)}
                    disabled={status.status === 'Resolved' || status.status === 'False_Positive' || status.status === 'Verified_Risk'}
                  >
                    Acknowledge
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </SectionCard>
    </div>
  );
}

function VetLabPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [details, setDetails] = useState<Record<string, AlertDetailResponse>>({});
  const [selectedAlertId, setSelectedAlertId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [vetForm, setVetForm] = useState({ vet_identifier: 'DEMO-VET-017', notes: 'Demonstration review; not a clinical diagnosis.' });
  const [labForm, setLabForm] = useState({ sample_identifier: 'DEMO-SAMPLE-01', requested_tests: 'Demo screening panel, Demo culture', notes: 'Synthetic referral record for administrative workflow.' });
  const [labReferral, setLabReferral] = useState<LabReferralResponse | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const statuses = await api.getEscalationStatus();
      const nextDetails = Object.fromEntries(
        (
          await Promise.all(
            statuses.map(async (status) => {
              try {
                const detail = await api.getAlertDetail(status.alert_id);
                return [status.alert_id, detail] as const;
              } catch {
                return null;
              }
            }),
          )
        ).filter((entry): entry is readonly [string, AlertDetailResponse] => Boolean(entry)),
      );
      setDetails(nextDetails);
      const firstUnderReview = Object.values(nextDetails).find((detail) => detail.alert.status === 'Under_Vet_Review');
      setSelectedAlertId(firstUnderReview ? firstUnderReview.alert.id : null);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load vet and lab workflow.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const alertIds = Object.keys(details).filter((id) => details[id].alert.status === 'Under_Vet_Review' || details[id].alert.status === 'Verified_Risk');
  const selectedAlert = selectedAlertId ? details[selectedAlertId] : null;

  const handleVetSubmit = async (outcome: VetOutcome) => {
    if (!selectedAlert) return;
    try {
      const result = await api.submitVetVerification({
        alert_id: selectedAlert.alert.id,
        outcome,
        vet_identifier: vetForm.vet_identifier,
        notes: vetForm.notes,
      });
      setStatusMessage(`${result.verification_result} recorded: ${result.alert_status}`);
      await load();
    } catch (caughtError) {
      setStatusMessage(caughtError instanceof Error ? caughtError.message : 'Verification failed.');
    }
  };

  const handleLabCreate = async () => {
    if (!selectedAlert) return;
    try {
      const referral = await api.createLabReferral({
        alert_id: selectedAlert.alert.id,
        sample_identifier: labForm.sample_identifier,
        requested_tests: labForm.requested_tests.split(',').map((part) => part.trim()).filter(Boolean),
        notes: labForm.notes,
      });
      setLabReferral(referral);
      setStatusMessage(`Lab referral created: ${referral.status}`);
      await load();
    } catch (caughtError) {
      setStatusMessage(caughtError instanceof Error ? caughtError.message : 'Referral creation failed.');
    }
  };

  const handleLabStatus = async (status: 'Sample_Collected' | 'In_Lab' | 'Result_Available' | 'Cancelled', result?: string, notes?: string) => {
    if (!labReferral) return;
    try {
      const updated = await api.updateLabReferralStatus(labReferral.id, status, result, notes);
      setLabReferral(updated);
      setStatusMessage(`Referral moved to ${status}`);
      await load();
    } catch (caughtError) {
      setStatusMessage(caughtError instanceof Error ? caughtError.message : 'Status update failed.');
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading vet and lab queue…</div>;
  }

  if (error) {
    return <BackendState error={error} onRetry={load} />;
  }

  if (!selectedAlert) {
    return <div className="empty-state"><h3>No alerts waiting for vet review</h3><p>The current backend has no active vet workflow.</p></div>;
  }

  return (
    <div className="stack gap-lg">
      <div className="filter-row">
        <label>
          Alert for review
          <select value={selectedAlertId ?? ''} onChange={(event) => setSelectedAlertId(event.target.value)}>
            {alertIds.map((id) => (
              <option value={id} key={id}>{details[id].device.device_uid}</option>
            ))}
          </select>
        </label>
      </div>

      <div className="row-two-col">
        <SectionCard title="Veterinary review">
          <div className="detail-list">
            <div><span>Acoustic event</span><strong>{selectedAlert.acoustic_event.event_type}</strong></div>
            <div><span>Confidence</span><strong>{(selectedAlert.acoustic_event.confidence_score * 100).toFixed(0)}%</strong></div>
            <div><span>Severity</span><strong>{selectedAlert.alert.anomaly_severity}</strong></div>
            <div><span>Alert status</span><strong>{selectedAlert.alert.status}</strong></div>
            <div><span>Current SLA tier</span><strong>{selectedAlert.sla.current_sla_tier}</strong></div>
          </div>
          <div className="form-grid">
            <label>
              Vet identifier
              <input value={vetForm.vet_identifier} onChange={(event) => setVetForm((existing) => ({ ...existing, vet_identifier: event.target.value }))} />
            </label>
            <label>
              Notes
              <textarea rows={4} value={vetForm.notes} onChange={(event) => setVetForm((existing) => ({ ...existing, notes: event.target.value }))} />
            </label>
          </div>
          <div className="action-row">
            <button type="button" className="primary-button" onClick={() => handleVetSubmit('Verified_Risk')}>Verified risk</button>
            <button type="button" className="secondary-button" onClick={() => handleVetSubmit('False_Positive')}>False positive</button>
          </div>
        </SectionCard>

        <SectionCard title="Lab referral">
          <div className="form-grid">
            <label>
              Sample identifier
              <input value={labForm.sample_identifier} onChange={(event) => setLabForm((existing) => ({ ...existing, sample_identifier: event.target.value }))} />
            </label>
            <label>
              Requested tests
              <input value={labForm.requested_tests} onChange={(event) => setLabForm((existing) => ({ ...existing, requested_tests: event.target.value }))} />
            </label>
            <label>
              Notes
              <textarea rows={3} value={labForm.notes} onChange={(event) => setLabForm((existing) => ({ ...existing, notes: event.target.value }))} />
            </label>
          </div>
          <div className="action-row">
            <button type="button" className="primary-button" onClick={handleLabCreate}>Create referral</button>
          </div>
          {labReferral && (
            <div className="detail-list compact">
              <div><span>Status</span><strong>{labReferral.status}</strong></div>
              <div><span>Sample</span><strong>{labReferral.sample_identifier}</strong></div>
              <div><span>Requested</span><strong>{labReferral.requested_tests.join(', ')}</strong></div>
            </div>
          )}
          {labReferral && (
            <div className="action-row">
              <button type="button" className="secondary-button" onClick={() => handleLabStatus('Sample_Collected')}>Sample collected</button>
              <button type="button" className="secondary-button" onClick={() => handleLabStatus('In_Lab')}>In lab</button>
              <button type="button" className="secondary-button" onClick={() => handleLabStatus('Result_Available', 'DEMO: Screening result recorded for demo')}>
                Result available
              </button>
            </div>
          )}
        </SectionCard>
      </div>

      {statusMessage && <div className="status-banner">{statusMessage}</div>}
    </div>
  );
}

function EdgeMonitorPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [devices, setDevices] = useState<AlertDetailResponse[]>([]);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const statuses = await api.getEscalationStatus();
      const detailEntries = await Promise.all(
        statuses.map(async (status) => {
          try {
            return await api.getAlertDetail(status.alert_id);
          } catch {
            return null;
          }
        }),
      );
      setDevices(detailEntries.filter(Boolean) as AlertDetailResponse[]);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load device telemetry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return <div className="panel-loading">Loading edge monitoring…</div>;
  }

  if (error) {
    return <BackendState error={error} onRetry={load} />;
  }

  return (
    <div className="stack gap-lg">
      <div className="legacy-flow">
        <span>OFFLINE</span>
        <span className="arrow">→</span>
        <span>LOCAL QUEUE</span>
        <span className="arrow">→</span>
        <span>SYNCING</span>
        <span className="arrow">→</span>
        <span>ACKNOWLEDGED</span>
      </div>
      <SectionCard title="Demo Edge Simulator">
        <div className="table-list">
          {devices.length ? (
            devices.map((detail) => (
              <div className="alert-row" key={detail.device.id}>
                <div>
                  <div className="row-title">{detail.device.device_uid}</div>
                  <div className="muted">{detail.shed.shed_number}</div>
                </div>
                <div>
                  <div className="row-title">Status</div>
                  <StatusBadge value={detail.device.status} />
                </div>
                <div>
                  <div className="row-title">Firmware</div>
                  <div className="muted">{detail.device.firmware_version}</div>
                </div>
                <div>
                  <div className="row-title">Last heartbeat</div>
                  <div className="muted">{formatDate(detail.device.last_heartbeat_at)}</div>
                </div>
                <div>
                  <div className="row-title">Sync</div>
                  <div className="muted">{detail.acoustic_event.is_synced_offline ? 'Queued locally' : 'Directly synced'}</div>
                </div>
              </div>
            ))
          ) : (
            <p className="muted">No device telemetry is currently available from the backend.</p>
          )}
        </div>
      </SectionCard>
    </div>
  );
}

function AuditLedgerPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [blocks, setBlocks] = useState<AuditBlockResponse[]>([]);
  const [integrity, setIntegrity] = useState<{ valid: boolean; checked_blocks: number; error: string | null } | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getAuditChain();
      setBlocks(response);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : 'Unable to load audit ledger.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const verify = async () => {
    try {
      const result = await api.verifyAuditIntegrity();
      setIntegrity(result);
    } catch (caughtError) {
      setIntegrity({ valid: false, checked_blocks: 0, error: caughtError instanceof Error ? caughtError.message : 'Verification failed.' });
    }
  };

  if (loading) {
    return <div className="panel-loading">Loading tamper-evident audit ledger…</div>;
  }

  if (error) {
    return <BackendState error={error} onRetry={load} />;
  }

  return (
    <div className="stack gap-lg">
      <SectionCard title="Tamper-evident Audit Ledger" actions={<button type="button" className="primary-button" onClick={verify}>Verify Integrity</button>}>
        <div className="table-list compact-table">
          {blocks.length ? (
            blocks.map((block) => (
              <div className="table-row ledger-row" key={`${block.block_index}-${block.block_hash}`}>
                <span>#{block.block_index}</span>
                <span>{formatDate(block.timestamp)}</span>
                <span>{block.entity_type}</span>
                <span>{block.entity_id}</span>
                <span className="mono">{block.payload_hash.slice(0, 12)}…</span>
                <span className="mono">{block.block_hash.slice(0, 12)}…</span>
              </div>
            ))
          ) : (
            <p className="muted">No audit blocks are available.</p>
          )}
        </div>
      </SectionCard>

      {integrity && (
        <div className={`integrity-box ${integrity.valid ? 'success' : 'warning'}`}>
          <strong>{integrity.valid ? '✓ Chain integrity verified' : '⚠ Integrity verification failed'}</strong>
          <p>
            Checked blocks: {integrity.checked_blocks}
            {integrity.error ? ` • ${integrity.error}` : ''}
          </p>
        </div>
      )}
    </div>
  );
}

function GovernmentExportPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [payload, setPayload] = useState<unknown>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.getGovernmentExport();
      setPayload(response);
    } catch (caughtError) {
      setError(caughtError instanceof Error ? caughtError.message : backendUnavailableMessage);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) {
    return <div className="panel-loading">Loading export workflow…</div>;
  }

  if (error) {
    return <BackendState error={error} actionLabel="Retry export status" onRetry={load} />;
  }

  return (
    <div className="stack gap-lg">
      <SectionCard title="NADRES / Bharat Pashudhan-ready structured export">
        <pre className="json-block">{JSON.stringify(payload, null, 2)}</pre>
      </SectionCard>
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState<PageKey>('command-center');

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand-block">
          <div className="brand-mark">ALH</div>
          <div>
            <div className="brand-name">Acoustic Livestock Health</div>
            <div className="brand-subtitle">Command Center</div>
          </div>
        </div>

        <nav className="nav-list" aria-label="Main navigation">
          {navItems.map((item) => (
            <button
              key={item.key}
              type="button"
              className={activePage === item.key ? 'nav-button active' : 'nav-button'}
              onClick={() => setActivePage(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="disclaimer-box">
          <strong>Medical disclaimer</strong>
          <p>{medicalDisclaimer}</p>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div>
            <p className="eyebrow">SIH 2026</p>
            <h1>Livestock Health Command Center</h1>
          </div>
          <div className="status-indicator" role="status">
            <span className="status-dot" aria-hidden="true" />
            Backend status: live
          </div>
        </header>

        {activePage === 'command-center' && <CommandCenterPage />}
        {activePage === 'alerts-sla' && <AlertsSlaPage />}
        {activePage === 'vet-lab' && <VetLabPage />}
        {activePage === 'edge-monitor' && <EdgeMonitorPage />}
        {activePage === 'audit-ledger' && <AuditLedgerPage />}
        {activePage === 'government-export' && <GovernmentExportPage />}
      </main>
    </div>
  );
}

export default App;
