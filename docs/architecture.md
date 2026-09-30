# High-Level Architecture

## Planned System

```text
Shed Microphone
      |
      v
Edge AI Device
      |
      v
Audio Preprocessing
      |
      v
YAMNet + Classifier
      |
      v
TensorFlow Lite
      |
      v
Local SQLite Store
      |
      v
Offline Store-and-Forward Sync
      |
      v
FastAPI Backend
      |
      v
PostgreSQL
      |
      v
Alert / Escalation
      |
      v
Veterinary Verification
      |
      v
Lab Referral
      |
      v
Geospatial Dashboard
      |
      v
Government Data Export
```

A tamper-evident cryptographic audit ledger is also planned. The approved milestone order is recorded in [implementation-plan.md](implementation-plan.md).

## Current Checkpoint: Milestone 4

The backend persists `Farm`, `Shed`, `Device`, `AcousticEvent`, `Alert`, and `EscalationRecord` records in PostgreSQL using SQLAlchemy's async engine. Alembic owns the PostgreSQL schema migration. The edge API supports signed single-event ingestion, SHA-256-verified batch sync with idempotency, and device heartbeat updates. High/Critical alert SLA deadlines are evaluated deterministically from persisted tier timestamps; mock SMS/voice adapters record demo delivery without external providers. Seed data targets PostgreSQL only. The ML service preprocesses WAV audio to mono 16 kHz float32 and uses pretrained YAMNet only to produce 1024-dimensional embeddings; its separate demo classifier is deterministic but untrained.

All alerts are acoustic anomaly early warnings and require veterinary verification. The system is not an automated diagnosis tool. Veterinary/laboratory workflows, the audit ledger, edge-local storage, and the full dashboard remain future milestones. Synthetic audio is demonstration-only and is not livestock recording data.
