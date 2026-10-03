# High-Level Architecture

## Current System Overview

The SIH 2026 acoustic livestock health demo is a four-part system:

```text
Shed microphone / edge device
  ↓
Edge simulator with local SQLite queue
  ↓
Signed batch sync to backend
  ↓
FastAPI backend backed by PostgreSQL
  ↓
Alerting, escalation, vet review, lab referral
  ↓
Tamper-evident SHA-256 audit ledger
  ↓
React + TypeScript dashboard
```

## Service Responsibilities

### Edge simulator

The edge simulator is designed for local-first operation. It records device events in a SQLite queue when network access fails or the backend is unavailable. Each event uses the same HMAC-SHA256 signing contract as the central backend, then synchronizes as a batch with a maximum size of 50 and a SHA-256 batch hash check.

Key behaviors:

- queue storage in SQLite only
- local offline buffering
- automatic retry on failed sync
- idempotent behavior during re-sync
- online/offline status and heartbeat support
- queue inspection and CLI command flow

### Backend

The central backend persists the operational model in PostgreSQL and exposes the API workflows used by the frontend and the simulator.

Core domains:

- farms, sheds, devices
- acoustic events
- alerts and escalation records
- vet verification and lab referral tracking
- tamper-evident audit ledger

The backend validates request state and enforces workflow rules such as:

- acknowledgement only on the current SLA tier
- vet verification only for Under_Vet_Review alerts
- duplicate verification rejection
- single referral per Verified_Risk alert
- valid lab status transitions only

### ML service

The ML service preprocesses audio, extracts YAMNet embeddings, and uses a demo classifier. It remains a prototype and intentionally does not claim clinical accuracy or livestock performance metrics.

Important constraints:

- embedding dimension is 1024
- prediction results are demo-only and unlabeled
- classifier_status is UNTRAINED_DEMO
- the project does not ship trained livestock weights

### Frontend dashboard

The frontend consumes the real backend contracts and renders the operational views:

- Command Center
- Alerts & SLA
- Vet / Lab Workbench
- Edge Monitor
- Audit Ledger
- Government Export

The UI deliberately shows the real available backend state and empty/unavailable states when an endpoint is not implemented.

## Data and Security Notes

- The central backend does not use SQLite.
- SQLite is only used in the edge simulator local queue.
- HMAC signing is shared-secret based and matches the backend verification contract.
- The audit ledger is a tamper-evident SHA-256 ledger, not a blockchain.
- All alert and workflow outcomes remain advisory and require human review.

## Medical Boundary

"Acoustic Early-Warning & Anomaly Detection only." The system does not diagnose disease or prescribe treatment. Veterinary clinical verification remains required throughout the workflow.

## Current Checkpoint

The repository is verified at the M9 stage with the following behaviors in place:

- operational backend API contract
- edge offline queue and sync workflow
- ML inference pipeline and demo classifier semantics
- SLA-based escalation and vet/lab review cycle
- tamper-evident audit hashing and integrity checks
- frontend dashboard integrated with the real backend API

Live PostgreSQL/Docker execution is not claimed here because the database environment was unavailable during verification.
