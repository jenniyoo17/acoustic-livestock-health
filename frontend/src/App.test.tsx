import { cleanup, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import App from './App';

describe('App shell and dashboard', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn((input: RequestInfo | URL) => {
      const url = String(input);

      if (url.endsWith('/api/v1/alerts/escalation-status')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              alert_id: '11111111-1111-1111-1111-111111111111',
              status: 'Under_Vet_Review',
              current_sla_tier: 'Tier_2_Field_Vet',
              triggered_at: '2026-09-30T12:00:00Z',
              deadline: '2026-09-30T12:45:00Z',
              remaining_seconds: 2700,
              sla_enabled: true,
              sla_breached: false,
              acknowledged_at: null,
              escalation_history: [],
            },
          ],
        });
      }

      if (url.includes('/api/v1/alerts/11111')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            alert: {
              id: '11111111-1111-1111-1111-111111111111',
              acoustic_event_id: '22222222-2222-2222-2222-222222222222',
              shed_id: '33333333-3333-3333-3333-333333333333',
              anomaly_severity: 'High',
              status: 'Under_Vet_Review',
              current_sla_tier: 'Tier_2_Field_Vet',
              triggered_at: '2026-09-30T12:00:00Z',
              resolved_at: null,
            },
            acoustic_event: {
              id: '22222222-2222-2222-2222-222222222222',
              device_id: '44444444-4444-4444-4444-444444444444',
              shed_id: '33333333-3333-3333-3333-333333333333',
              event_type: 'Cough',
              confidence_score: 0.91,
              yamnet_embedding_vector: [0.1, 0.2],
              audio_duration_sec: 1.5,
              audio_snippet_url: null,
              recorded_at: '2026-09-30T12:00:00Z',
              is_synced_offline: false,
              created_at: '2026-09-30T12:00:00Z',
            },
            shed: {
              id: '33333333-3333-3333-3333-333333333333',
              farm_id: '55555555-5555-5555-5555-555555555555',
              shed_number: 'SH-01',
              animal_type: 'Cattle',
              capacity: 50,
              current_count: 28,
              created_at: '2026-09-30T00:00:00Z',
            },
            device: {
              id: '44444444-4444-4444-4444-444444444444',
              shed_id: '33333333-3333-3333-3333-333333333333',
              device_uid: 'MIC-TEST-01',
              firmware_version: '0.1.0',
              status: 'Online',
              public_key: null,
              last_heartbeat_at: '2026-09-30T11:59:00Z',
              created_at: '2026-09-30T00:00:00Z',
            },
            sla: {
              alert_id: '11111111-1111-1111-1111-111111111111',
              status: 'Under_Vet_Review',
              current_sla_tier: 'Tier_2_Field_Vet',
              triggered_at: '2026-09-30T12:00:00Z',
              deadline: '2026-09-30T12:45:00Z',
              remaining_seconds: 2700,
              sla_enabled: true,
              sla_breached: false,
              acknowledged_at: null,
              escalation_history: [],
            },
          }),
        });
      }

      if (url.endsWith('/api/v1/audit/chain')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [
            {
              block_index: 0,
              timestamp: '1970-01-01T00:00:00Z',
              previous_hash: null,
              entity_type: 'GENESIS',
              entity_id: '0',
              payload_hash: 'abc123',
              block_hash: 'def456',
            },
          ],
        });
      }

      if (url.endsWith('/api/v1/audit/verify-integrity')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ valid: true, checked_blocks: 1, error: null }),
        });
      }

      if (url.endsWith('/api/v1/vet/verify')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            verification_id: 'abcd',
            alert_id: '11111111-1111-1111-1111-111111111111',
            verification_result: 'Verified_Risk',
            alert_status: 'Verified_Risk',
            vet_identifier: 'DEMO-VET-017',
            verified_at: '2026-09-30T12:10:00Z',
          }),
        });
      }

      if (url.endsWith('/api/v1/lab/referrals')) {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
            alert_id: '11111111-1111-1111-1111-111111111111',
            verification_id: 'abcd',
            sample_identifier: 'DEMO-SAMPLE-01',
            requested_tests: ['Demo screening panel'],
            status: 'Pending',
            referred_at: '2026-09-30T12:10:00Z',
            result: null,
            result_at: null,
            notes: 'Synthetic referral record for presentation.',
            is_demo_result: false,
            created_at: '2026-09-30T12:10:00Z',
          }),
        });
      }

      if (url.includes('/api/v1/lab/referrals/')) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            referral: {
              id: 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee',
              alert_id: '11111111-1111-1111-1111-111111111111',
              verification_id: 'abcd',
              sample_identifier: 'DEMO-SAMPLE-01',
              requested_tests: ['Demo screening panel'],
              status: 'Pending',
              referred_at: '2026-09-30T12:10:00Z',
              result: null,
              result_at: null,
              notes: 'Synthetic referral record for presentation.',
              is_demo_result: false,
              created_at: '2026-09-30T12:10:00Z',
            },
            alert: {
              id: '11111111-1111-1111-1111-111111111111',
              acoustic_event_id: '22222222-2222-2222-2222-222222222222',
              shed_id: '33333333-3333-3333-3333-333333333333',
              anomaly_severity: 'High',
              status: 'Verified_Risk',
              current_sla_tier: 'Tier_2_Field_Vet',
              triggered_at: '2026-09-30T12:00:00Z',
              resolved_at: null,
            },
            verification: {
              id: 'abcd',
              alert_id: '11111111-1111-1111-1111-111111111111',
              vet_identifier: 'DEMO-VET-017',
              verification_status: 'Verified_Risk',
              assessment_notes: 'Validation example',
              verified_at: '2026-09-30T12:10:00Z',
              created_at: '2026-09-30T12:10:00Z',
            },
          }),
        });
      }

      if (url.endsWith('/api/v1/geo/outbreak-clusters')) {
        return Promise.resolve({ ok: false, status: 404, json: async () => ({ detail: 'Not found' }) });
      }

      if (url.endsWith('/api/v1/export/government-nadrs')) {
        return Promise.resolve({ ok: false, status: 404, json: async () => ({ detail: 'Not found' }) });
      }

      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    }));
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it('renders the app shell and medical disclaimer', () => {
    render(<App />);

    expect(screen.getByText('Livestock Health Command Center')).toBeInTheDocument();
    expect(screen.getByText(/Acoustic Early-Warning & Anomaly Detection only/i)).toBeInTheDocument();
    expect(screen.getByText(/This system does not diagnose or prescribe treatment/i)).toBeInTheDocument();
  });

  it('shows the command center summary after loading backend data', async () => {
    render(<App />);

    expect(await screen.findByText('Total alerts')).toBeInTheDocument();
    expect(screen.getAllByText('1').length).toBeGreaterThan(0);
  });

  it('supports navigation between the main workspaces', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: 'Alerts & SLA' }));
    expect(screen.getByText('Operations board')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Vet / Lab Workbench' }));
    expect(screen.getByText('Veterinary review')).toBeInTheDocument();
  });

  it('shows the audit ledger and integrity verification result', async () => {
    const user = userEvent.setup();
    render(<App />);

    await user.click(screen.getByRole('button', { name: 'Audit Ledger' }));
    expect(await screen.findByText('Tamper-evident Audit Ledger')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Verify Integrity' }));
    expect(await screen.findByText(/Chain integrity verified/i)).toBeInTheDocument();
  });
});
