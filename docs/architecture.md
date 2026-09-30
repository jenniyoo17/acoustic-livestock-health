# Architecture Documentation

## System Overview
The **SIH 2026 Acoustic Livestock Health Early-Warning System** is an offline-first, AI-driven monitoring platform that analyzes shed acoustic signals (coughing, distress vocalizations, rumination anomalies) to detect early indicators of livestock respiratory illness.

> **Medical Disclaimer**: This system generates statistical anomaly alerts requiring clinical verification by a registered veterinarian. It does **NOT** provide automated medical diagnoses or treatment prescriptions.

## High-Level Architecture

```
[Shed Microphones] ──> [Edge AI Device (TFLite YAMNet Classifier)]
                               │
                       (Store & Forward)
                               │
                       [FastAPI Gateway]
                               ├──> [PostgreSQL Database (SQLAlchemy 2.0 Async)]
                               ├──> [Python ML Microservice (Re-Validation)]
                               ├──> [SLA Escalation Engine]
                               ├──> [Tamper-Evident Ledger (Audit Hash Chain)]
                               └──> [React + TypeScript Dashboard]
```

## Database Models & Entities (Milestone 2)
1. **`Farm`**: Farm details, owner contact, GPS coordinates (`latitude`, `longitude`), `district`, `state`.
2. **`Shed`**: Farm shed unit, `animal_type` (`Cattle`, `Buffalo`, `Goat`, `Sheep`), capacity, current animal count.
3. **`Device`**: Shed-mounted microphone sensor, `device_uid`, `firmware_version`, `status` (`Online`, `Offline`, `Degraded`), `last_heartbeat_at`.
4. **`AcousticEvent`**: Acoustic anomaly record, `event_type` (`Cough`, `Distress_Call`, `Abnormal_Rumination`, `Environmental_Noise`), `confidence_score` (0.0-1.0), `yamnet_embedding_vector`, `audio_duration_sec`, `recorded_at`, `is_synced_offline`.
5. **`Alert`**: Health risk alert, `anomaly_severity` (`Low`, `Medium`, `High`, `Critical`), `status` (`Pending_Triage`, `Escalated`, `Under_Vet_Review`, `Verified_Risk`, `False_Positive`, `Resolved`), `current_sla_tier`.

## Edge Ingestion Protocols
- **`POST /api/v1/edge/ingest`**: Real-time event ingestion with automatic anomaly evaluation and alert generation.
- **`POST /api/v1/edge/sync-batch`**: Store-and-forward batch ingestion (up to 50 events) with idempotency duplicate checking.
- **`POST /api/v1/edge/heartbeat`**: Edge device status and firmware telemetry update.
